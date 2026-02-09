import logging
from typing import Optional

from .crawler import WebsiteCrawler
from .models import ContactInfo, ParserSettings

logger = logging.getLogger(__name__)


class ContactParser:
    """Основной класс парсера для извлечения контактной информации с сайтов"""

    def __init__(self, settings: Optional[ParserSettings] = None):
        """
        Инициализация парсера

        Args:
            settings: Настройки парсера (если None, используются настройки по умолчанию)
        """
        self.settings = settings or ParserSettings()
        self.crawler = WebsiteCrawler(self.settings)

        logger.info(
            f"Парсер инициализирован с настройками: "
            f"max_pages={self.settings.max_pages}, "
            f"timeout={self.settings.timeout}, "
            f"workers={self.settings.max_workers}"
        )

    def parse_website(self, start_url: str) -> ContactInfo:
        """
        Парсит сайт и возвращает контактную информацию

        Args:
            start_url: Стартовый URL для парсинга

        Returns:
            ContactInfo: Объект с контактной информацией
        """
        logger.info(f"Начинаем парсинг сайта: {start_url}")

        try:
            # Обходим сайт
            crawled_pages = self.crawler.crawl(start_url)

            # Собираем все контакты
            all_emails = set()
            all_phones = set()

            for page in crawled_pages:
                if page:
                    all_emails.update(page.get("emails", set()))
                    all_phones.update(page.get("phones", set()))

            # Создаем результат
            result = ContactInfo(url=start_url, emails=list(all_emails), phones=list(all_phones))

            logger.info(
                f"Парсинг завершен. Найдено: " f"{len(result.emails)} email, " f"{len(result.phones)} телефонов"
            )

            return result

        except Exception as e:
            logger.error(f"Ошибка при парсинге {start_url}: {e}")
            try:
                return ContactInfo(url=start_url, emails=[], phones=[])
            except Exception:
                return ContactInfo(url="https://error.invalid", emails=[], phones=[])
