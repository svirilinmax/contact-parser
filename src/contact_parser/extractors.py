import logging
import re
from typing import Set

from lxml.html import HtmlElement

from .models import ParserSettings
from .utils import HTMLParser, PatternMatcher
from .validators import EmailValidator, PhoneValidator

logger = logging.getLogger(__name__)


class DataExtractor:
    """Класс для извлечения данных с валидацией через единые валидаторы"""

    def __init__(self, settings: ParserSettings):
        self.settings = settings
        self.html_parser = HTMLParser()
        self.pattern_matcher = PatternMatcher()

        # Инициализируем валидаторы
        self.phone_validator = PhoneValidator()
        self.email_validator = EmailValidator()

        # Компилируем паттерны из НАСТРОЕК (не дублируем константы!)
        self.email_pattern = re.compile(self.settings.email_pattern, re.IGNORECASE)

        # Паттерны телефонов - берём ТОЛЬКО из настроек!
        self.phone_patterns = self.pattern_matcher.compile_patterns(self.settings.phone_patterns)

        # НЕ СОЗДАЁМ своих паттернов! Используем настройки.
        # Если нужны дополнительные паттерны - добавляем их в settings.phone_patterns

    def extract_from_html(self, html: str, current_url: str = "") -> dict:
        """
        Основной метод для извлечения данных из HTML

        Args:
            html: HTML код страницы
            current_url: URL текущей страницы (для контекстной валидации)
        """
        result = {"emails": set(), "phones": set(), "links": set()}

        try:
            # Парсим HTML
            tree = self.html_parser.parse_html(html)
            if tree is None:
                logger.warning("Не удалось распарсить HTML")
                return result

            # Извлекаем текст для поиска
            text = self.html_parser.extract_text(tree)

            # 1. ИЗВЛЕКАЕМ EMAIL
            result["emails"] = self._extract_emails(text, tree)

            # 2. ИЗВЛЕКАЕМ ТЕЛЕФОНЫ
            if self.settings.enable_phone_validation:
                # С валидацией - передаём current_url для контекста домена
                result["phones"] = self._extract_phones_with_validation(text, tree, current_url)
            else:
                # Без валидации - просто собираем всё
                result["phones"] = self._extract_phones_raw(text, tree)

            # 3. ИЗВЛЕКАЕМ ССЫЛКИ
            result["links"] = self._extract_links(tree)

            logger.debug(
                f"Страница {current_url}: "
                f"найдено {len(result['emails'])} email, "
                f"{len(result['phones'])} телефонов, "
                f"{len(result['links'])} ссылок"
            )

            return result

        except Exception as e:
            logger.error(f"Ошибка при извлечении данных из HTML: {e}")
            return result

    def _extract_emails(self, text: str, tree: HtmlElement) -> Set[str]:
        """Извлекает email адреса"""

        emails = set()

        try:
            # 1. Ищем в тексте страницы
            found_emails = self.email_pattern.findall(text)
            for email in found_emails:
                clean_email = email.strip()
                if clean_email:
                    emails.add(clean_email)

            # 2. Ищем в mailto: ссылках
            mailto_links = tree.xpath('//a[starts-with(@href, "mailto:")]/@href')
            for mailto in mailto_links:
                # Извлекаем email из mailto:email@domain.com
                email = mailto.replace("mailto:", "").strip()
                # Отсекаем параметры после ?
                email = email.split("?")[0].split("&")[0]
                if email and "@" in email:
                    emails.add(email)

            # 3. Ищем в data-атрибутах и других местах (опционально)
            if tree is not None:
                data_emails = tree.xpath("//*[@data-email]/@data-email")
                for email in data_emails:
                    if email and "@" in email:
                        emails.add(email)

        except Exception as e:
            logger.error(f"Ошибка при извлечении email: {e}")

        # Валидируем через EmailValidator
        if self.settings.enable_email_validation:
            return set(self.email_validator.validate_and_normalize_emails(emails))
        else:
            # Просто нормализуем
            normalized = set()
            for email in emails:
                normalized_email = self.email_validator.normalize_email(email)
                if normalized_email and "@" in normalized_email:
                    normalized.add(normalized_email)
            return normalized

    def _extract_phones_with_validation(self, text: str, tree: HtmlElement, current_url: str = "") -> Set[str]:
        """
        Извлекает телефонные номера с полной валидацией через PhoneValidator
        """
        phones = set()

        try:
            # 1. Ищем в тексте по паттернам из настроек
            phones.update(self.pattern_matcher.find_all_matches(text, self.phone_patterns))

            # 2. Ищем в tel: ссылках
            tel_links = tree.xpath('//a[starts-with(@href, "tel:")]/@href')
            for tel in tel_links:
                phone = tel.replace("tel:", "").strip()
                phone = phone.split("?")[0].split("&")[0]
                if phone:
                    phones.add(phone)

            # 3. Ищем в атрибутах data-phone
            data_phones = tree.xpath("//*[@data-phone]/@data-phone")
            for phone in data_phones:
                if phone:
                    phones.add(phone)

            # 4. Ищем в meta тегах с телефонами
            meta_phones = tree.xpath('//meta[@name="telephone" or @property="telephone"]/@content')
            for phone in meta_phones:
                if phone:
                    phones.add(phone)

        except Exception as e:
            logger.error(f"Ошибка при извлечении телефонов: {e}")

        validated_phones = self.phone_validator.validate_and_normalize_phones(phones, current_url)

        logger.debug(f"Извлечено {len(phones)} сырых номеров, после валидации: {len(validated_phones)}")

        return set(validated_phones)

    def _extract_phones_raw(self, text: str, tree: HtmlElement, current_url: str = "") -> Set[str]:
        """Извлекает телефоны БЕЗ строгой валидации (только базовая очистка)"""

        phones = set()

        try:
            # Ищем по всем паттернам
            phones.update(self.pattern_matcher.find_all_matches(text, self.phone_patterns))

            # Ищем в tel ссылках
            tel_links = tree.xpath('//a[starts-with(@href, "tel:")]/@href')
            for tel in tel_links:
                phone = tel.replace("tel:", "").strip()
                phones.add(phone)

        except Exception as e:
            logger.error(f"Ошибка при извлечении телефонов: {e}")

        # Только базовая нормализация, без строгой валидации
        normalized = set()
        for phone in phones:
            # Используем _clean_phone напрямую, без is_likely_phone
            cleaned = self.phone_validator._clean_phone(phone)
            if cleaned and len(cleaned.lstrip("+")) >= 7:
                normalized.add(cleaned)

        return normalized

    def _extract_links(self, tree: HtmlElement) -> Set[str]:
        """Извлекает все ссылки из HTML"""

        links = set()

        try:
            link_elements = tree.xpath("//a[@href]")
            for element in link_elements:
                href = element.get("href", "").strip()
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
                    links.add(href)

            # Ссылки в meta refresh
            meta_refresh = tree.xpath('//meta[@http-equiv="refresh"]/@content')
            for content in meta_refresh:
                url_match = re.search(r"url=([^\s]+)", content, re.IGNORECASE)
                if url_match:
                    links.add(url_match.group(1))

            canonical = tree.xpath('//link[@rel="canonical"]/@href')
            for link in canonical:
                if link:
                    links.add(link)

        except Exception as e:
            logger.error(f"Ошибка при извлечении ссылок: {e}")

        return links
