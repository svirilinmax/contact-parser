import logging
import re
from typing import List, Optional, Pattern, Set
from urllib.parse import urljoin, urlparse

from lxml.etree import ParserError
from lxml.html import HtmlElement, fromstring

logger = logging.getLogger(__name__)


class URLNormalizer:
    """Класс для нормализации и валидации URL с использованием lxml"""

    @staticmethod
    def normalize_url(url: str, base_url: str) -> Optional[str]:
        """Нормализует URL, преобразуя относительные ссылки в абсолютные"""

        # Убираем лишние пробелы по краям
        url = url.strip() if url else ""

        try:
            # Добавляем проверку на пустую строку в условие
            if not url or url.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
                return None

            # Преобразуем относительный URL в абсолютный
            absolute_url = urljoin(base_url, url)

            # Парсим URL для нормализации
            parsed = urlparse(absolute_url)

            # Проверяем наличие схемы и домена
            if not parsed.scheme or not parsed.netloc:
                return None

            # Создаем нормализованный URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"  # noqa E231

            # Убираем trailing slash для единообразия
            normalized = normalized.rstrip("/")

            return normalized
        except Exception as e:
            logger.debug(f"Ошибка при нормализации URL {url}: {e}")
            return None

    @staticmethod
    def is_same_domain(url: str, base_domain: str) -> bool:
        """Проверяет, принадлежит ли URL тому же домену"""

        if not url or not url.strip():
            return False

        try:
            parsed = urlparse(url)

            if parsed.netloc:
                return parsed.netloc == base_domain or parsed.netloc.endswith(f".{base_domain}")
            if url.startswith(("/", "./", "../")):
                return True
            return False

        except Exception:
            return False

    @staticmethod
    def validate_url(url: str) -> bool:
        """Проверяет валидность URL"""

        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    @staticmethod
    def get_domain(url: str) -> Optional[str]:
        """Извлекает домен из URL"""

        if not url or not url.strip():
            return None

        try:
            parsed = urlparse(url)

            if not parsed.netloc:
                if "." in url and "/" not in url.split(":")[0]:
                    return url
                return None

            return parsed.netloc
        except Exception:
            return None


class HTMLParser:
    """Класс для парсинга HTML с использованием lxml"""

    @staticmethod
    def parse_html(html: str) -> Optional[HtmlElement]:
        """Парсит HTML строку в lxml дерево"""

        try:
            return fromstring(html)
        except ParserError as e:
            logger.error(f"Ошибка парсинга HTML: {e}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при парсинге HTML: {e}")
            return None

    @staticmethod
    def extract_text(tree: HtmlElement) -> str:
        """Извлекает весь текст из HTML дерева"""

        if tree is None:
            return ""

        try:
            text = tree.text_content()
            # Убираем лишние пробелы и переносы
            text = re.sub(r"\s+", " ", text).strip()
            return text
        except Exception as e:
            logger.error(f"Ошибка при извлечении текста: {e}")
            return ""

    @staticmethod
    def extract_links(tree: HtmlElement, base_url: str) -> Set[str]:
        """Извлекает все ссылки из HTML дерева"""

        links = set()

        if tree is None:
            return links

        try:
            # Находим все ссылки с помощью XPath
            for link_element in tree.xpath("//a[@href]"):
                href = link_element.get("href", "").strip()
                if href:
                    links.add(href)

            logger.debug(f"Извлечено {len(links)} ссылок из HTML")
            return links

        except Exception as e:
            logger.error(f"Ошибка при извлечении ссылок: {e}")
            return links

    @staticmethod
    def clean_html(html: str) -> str:
        """Очищает HTML от лишних тегов и атрибутов"""

        try:
            tree = fromstring(html)

            # Удаляем скрипты и стили
            for element in tree.xpath("//script | //style | //noscript"):
                element.getparent().remove(element)

            # Возвращаем очищенный HTML
            cleaned = fromstring.tostring(tree, encoding="unicode", method="html")
            return cleaned
        except Exception:
            # Если не удалось очистить, возвращаем исходный HTML
            return html


class PatternMatcher:
    """Класс для работы с регулярными выражениями"""

    @staticmethod
    def compile_patterns(patterns: List[str]) -> List[Pattern]:
        """Компилирует список регулярных выражений"""

        compiled = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as e:
                logger.error(f"Ошибка компиляции паттерна {pattern}: {e}")
        return compiled

    @staticmethod
    def find_all_matches(text: str, patterns: List[Pattern]) -> Set[str]:
        """Находит все совпадения по списку паттернов"""

        matches = set()

        for pattern in patterns:
            try:
                matches.update(pattern.findall(text))
            except Exception as e:
                logger.error(f"Ошибка при поиске по паттерну {pattern.pattern}: {e}")

        return matches
