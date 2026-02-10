import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional, Set

import requests

from .exceptions import ContentTypeError, NetworkError
from .extractors import DataExtractor
from .models import ParserSettings
from .utils import URLNormalizer

logger = logging.getLogger(__name__)


class WebsiteCrawler:
    """Класс для обхода веб-сайта с поддержкой многопоточности"""

    def __init__(self, settings: ParserSettings):
        self.settings = settings
        self.normalizer = URLNormalizer()
        self.data_extractor = DataExtractor(settings)

        # Создаем сессию для HTTP-запросов
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            }
        )
        self.session.max_redirects = 5

        # TODO: Добавить кэширование запросов для ускорения
        self._cache = {}  # Простой кэш в памяти

    def fetch_page(self, url: str) -> Optional[dict]:
        """Загружает страницу и возвращает её содержимое и метаданные"""

        # TODO: Проверить кэш перед загрузкой
        if url in self._cache:
            logger.debug(f"Используем кэшированную страницу: {url}")
            return self._cache[url]

        try:
            logger.debug(f"Загрузка страницы: {url}")

            response = self.session.get(
                url,
                timeout=self.settings.timeout,
                allow_redirects=self.settings.follow_redirects,
                verify=self.settings.verify_ssl,
            )
            response.raise_for_status()

            # Проверяем content-type
            content_type = response.headers.get("content-type", "").lower()
            if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                logger.warning(f"Неподдерживаемый content-type: {content_type} для {url}")
                raise ContentTypeError(f"Unsupported content type: {content_type}")

            # Проверяем размер контента
            content_length = len(response.content)
            if content_length > 10 * 1024 * 1024:  # 10MB
                logger.warning(f"Слишком большой контент: {content_length} байт для {url}")
                return None

            result = {
                "url": url,
                "html": response.text,
                "status_code": response.status_code,
                "content_type": content_type,
                "content_length": content_length,
                "final_url": response.url,
            }

            # TODO: Кэшируем результат
            self._cache[url] = result
            return result

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут при загрузке {url}")
            raise NetworkError(f"Timeout while fetching {url}")
        except requests.exceptions.TooManyRedirects:
            logger.error(f"Слишком много перенаправлений для {url}")
            raise NetworkError(f"Too many redirects for {url}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при загрузке {url}: {e}")
            raise NetworkError(f"Network error while fetching {url}: {e}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка при загрузке {url}: {e}")
            raise

    def process_page(self, url: str, base_domain: str) -> tuple:
        """Обрабатывает страницу: загружает и извлекает данные"""

        try:
            page_data = self.fetch_page(url)
            if not page_data:
                return url, None, set()

            # Извлекаем данные из HTML, передавая текущий URL
            extracted = self.data_extractor.extract_from_html(page_data["html"], url)

            # Фильтруем ссылки по домену
            filtered_links = set()
            for link in extracted["links"]:
                normalized = self.normalizer.normalize_url(link, url)
                if normalized and self.normalizer.is_same_domain(normalized, base_domain):
                    filtered_links.add(normalized)

            result = {
                "url": url,
                "emails": extracted["emails"],
                "phones": extracted["phones"],
                "links": filtered_links,
            }

            logger.info(f"Обработана страница: {url}")
            return url, result, filtered_links

        except (NetworkError, ContentTypeError) as e:
            logger.warning(f"Пропускаем страницу {url} из-за ошибки: {e}")
            return url, None, set()
        except Exception as e:
            logger.error(f"Ошибка при обработке страницы {url}: {e}")
            return url, None, set()

    def crawl(self, start_url: str, max_pages: Optional[int] = None) -> List[dict]:
        """Обходит сайт и возвращает список обработанных страниц"""

        if not self.normalizer.validate_url(start_url):
            raise ValueError(f"Некорректный URL: {start_url}")

        max_pages = max_pages or self.settings.max_pages
        base_domain = self.normalizer.get_domain(start_url)

        if not base_domain:
            raise ValueError(f"Не удалось извлечь домен из URL: {start_url}")

        logger.info(f"Начинаем обход сайта: {start_url}")
        logger.info(f"Домен: {base_domain}, Максимальное количество страниц: {max_pages}")

        visited: Set[str] = set()
        to_visit: Set[str] = {start_url}
        results: List[dict] = []

        # TODO: Добавить ограничение по времени выполнения
        start_time = time.time()
        max_time = self.settings.timeout * max_pages  # Максимальное время работы

        with ThreadPoolExecutor(max_workers=self.settings.max_workers) as executor:
            while to_visit and len(visited) < max_pages:
                # TODO: Проверка на превышение максимального времени
                if time.time() - start_time > max_time:
                    logger.warning(f"Превышено максимальное время работы ({max_time} сек)")
                    break

                # Выбираем страницы для обработки
                current_batch = list(to_visit)[: self.settings.max_workers]
                to_visit -= set(current_batch)

                # Отправляем задачи на выполнение
                future_to_url = {executor.submit(self.process_page, url, base_domain): url for url in current_batch}

                # Обрабатываем завершенные задачи
                for future in as_completed(future_to_url):
                    url = future_to_url[future]

                    try:
                        url, result, new_links = future.result(timeout=self.settings.timeout + 5)

                        visited.add(url)

                        if result:
                            results.append(result)

                            # Добавляем новые ссылки для обхода
                            for link in new_links:
                                if link not in visited and link not in to_visit:
                                    to_visit.add(link)

                    except Exception as e:
                        logger.error(f"Ошибка при обработке результата для {url}: {e}")
                        visited.add(url)

                # Задержка между батчами
                if self.settings.request_delay > 0:
                    time.sleep(self.settings.request_delay)

                logger.info(f"Прогресс: посещено {len(visited)}/{max_pages} страниц")

        if len(visited) >= max_pages:
            logger.info(f"Достигнут лимит в {max_pages} страниц")

        logger.info(f"Обход завершен. Обработано страниц: {len(results)}")
        return results
