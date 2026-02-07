import logging
import re
from typing import Set

from lxml.html import HtmlElement

from .models import ParserSettings
from .utils import HTMLParser, PatternMatcher
from .validators import EmailValidator, PhoneValidator

logger = logging.getLogger(__name__)


class DataExtractor:
    """Базовый класс для извлечения данных с универсальной валидацией"""

    def __init__(self, settings: ParserSettings):
        self.settings = settings
        self.html_parser = HTMLParser()
        self.pattern_matcher = PatternMatcher()

        # Инициализируем валидаторы
        self.phone_validator = PhoneValidator()
        self.email_validator = EmailValidator()

        # Компилируем паттерны
        self.email_pattern = re.compile(self.settings.email_pattern, re.IGNORECASE)
        self.phone_patterns = self.pattern_matcher.compile_patterns(self.settings.phone_patterns)

        # Универсальные паттерны для международных номеров
        self.universal_phone_patterns = [
            # Международный формат: +XXX XXX XXX XXX
            r"\+\d{1,4}[-\s]?\(?\d{1,5}\)?[-\s]?\d{1,5}[-\s]?\d{1,5}[-\s]?\d{1,5}",
            # Российские номера
            r"\+7[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            r"8[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Формы без кода страны
            r"\(?\d{3,4}\)?[-\s]?\d{2,3}[-\s]?\d{2,3}[-\s]?\d{2,4}",
            # Короткие форматы
            r"\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Белорусские номера
            r"\+375[-\s]?\d{2}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Казахстанские номера
            r"\+7[-\s]?\(?7\d{2}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Европейские форматы
            r"\+\d{2}[-\s]?\(?\d{2,4}\)?[-\s]?\d{3,4}[-\s]?\d{3,4}",
            # Американские/Канадские
            r"\+1[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}",
        ]

    def extract_from_html(self, html: str) -> dict:
        """Основной метод для извлечения данных из HTML"""

        result = {"emails": set(), "phones": set(), "links": set()}

        try:
            # Парсим HTML
            tree = self.html_parser.parse_html(html)
            if tree is None:
                return result

            # Извлекаем текст для поиска email и телефонов
            text = self.html_parser.extract_text(tree)

            # Извлекаем email
            result["emails"] = self._extract_emails(text, tree)

            # Извлекаем телефоны
            if self.settings.enable_phone_validation:
                result["phones"] = self._extract_phones_with_validation(text, tree)
            else:
                result["phones"] = self._extract_phones_universal(text, tree)

            # Извлекаем ссылки
            result["links"] = self._extract_links(tree)

            logger.debug(
                f"Извлечено: {len(result['emails'])} email, "
                f"{len(result['phones'])} телефонов, "
                f"{len(result['links'])} ссылок"
            )

            return result

        except Exception as e:
            logger.error(f"Ошибка при извлечении данных из HTML: {e}")
            return result

    def _extract_emails(self, text: str, tree: HtmlElement) -> Set[str]:
        """Извлекает email адреса с валидацией"""

        emails = set()

        # Ищем в тексте
        found_emails = self.email_pattern.findall(text)
        for email in found_emails:
            # Очищаем email от лишних символов
            clean_email = email.strip()
            if clean_email:
                emails.add(clean_email)

        # Ищем в mailto ссылках с помощью XPath
        try:
            mailto_links = tree.xpath('//a[starts-with(@href, "mailto:")]/@href')
            for mailto in mailto_links:
                email = mailto.replace("mailto:", "").strip()
                # Очищаем от параметров
                email = email.split("?")[0].split("&")[0]
                if self.email_pattern.match(email):
                    emails.add(email)
        except Exception as e:
            logger.error(f"Ошибка при извлечении email из mailto: {e}")

        # Валидируем и нормализуем email
        if self.settings.enable_email_validation:
            return set(self.email_validator.validate_and_normalize_emails(emails))
        else:
            # Без валидации - просто нормализуем
            normalized = set()
            for email in emails:
                normalized.add(email.lower().strip())
            return normalized

    def _extract_phones_with_validation(self, text: str, tree: HtmlElement) -> Set[str]:
        """Извлекает телефонные номера с улучшенной валидацией"""

        phones = set()

        # Ищем в тексте по всем паттернам
        phones.update(self.pattern_matcher.find_all_matches(text, self.phone_patterns))

        # Ищем по универсальным паттернам
        universal_patterns = self.pattern_matcher.compile_patterns(self.universal_phone_patterns)
        phones.update(self.pattern_matcher.find_all_matches(text, universal_patterns))

        # Ищем в tel ссылках
        try:
            tel_links = tree.xpath('//a[starts-with(@href, "tel:")]/@href')
            for tel in tel_links:
                phone = tel.replace("tel:", "").strip()
                # Очищаем от параметров
                phone = phone.split("?")[0].split("&")[0]
                phones.add(phone)
        except Exception as e:
            logger.error(f"Ошибка при извлечении телефонов из tel: {e}")

        # Валидируем и нормализуем телефоны
        return set(self.phone_validator.validate_and_normalize_phones(phones))

    def _extract_phones_universal(self, text: str, tree: HtmlElement) -> Set[str]:
        """Извлекает телефонные номера (универсальный метод для любых стран)"""

        phones = set()

        # 1. Ищем по базовым паттернам из настроек
        phones.update(self.pattern_matcher.find_all_matches(text, self.phone_patterns))

        # 2. Ищем по универсальным паттернам
        universal_patterns = self.pattern_matcher.compile_patterns(self.universal_phone_patterns)
        phones.update(self.pattern_matcher.find_all_matches(text, universal_patterns))

        # 3. Ищем в tel ссылках
        try:
            tel_links = tree.xpath('//a[starts-with(@href, "tel:")]/@href')
            for tel in tel_links:
                phone = tel.replace("tel:", "").strip()
                phones.add(phone)
        except Exception as e:
            logger.error(f"Ошибка при извлечении телефонов из tel: {e}")

        # 4. Фильтруем и нормализуем найденные телефоны
        valid_phones = set()
        for phone in phones:
            normalized = self._normalize_phone_universal(phone)
            if normalized and self._is_valid_phone_universal(normalized):
                valid_phones.add(normalized)

        return valid_phones

    def _extract_links(self, tree: HtmlElement) -> Set[str]:
        """Извлекает все ссылки из HTML"""

        links = set()

        try:
            # Используем XPath для извлечения ссылок
            link_elements = tree.xpath("//a[@href]")
            for element in link_elements:
                href = element.get("href", "").strip()
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    links.add(href)

            # Также проверяем ссылки в meta тегах
            meta_links = tree.xpath('//meta[@content and contains(@content, "http")]/@content')
            for meta_link in meta_links:
                if "http" in meta_link:
                    links.add(meta_link)

        except Exception as e:
            logger.error(f"Ошибка при извлечении ссылок: {e}")

        return links

    @staticmethod
    def _normalize_phone_universal(phone: str) -> str:
        """Нормализует телефонный номер (универсальный метод)"""

        if not phone:
            return ""

        # Сохраняем плюс в начале
        has_plus = phone.startswith("+")

        # Убираем все нецифровые символы, кроме +
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Убираем плюсы из середины строки
        if "+" in cleaned[1:]:
            cleaned = cleaned[0] + cleaned[1:].replace("+", "")

        # Если не было плюса, но номер выглядит как международный
        if not has_plus and len(cleaned) >= 10:
            # Российские номера
            if len(cleaned) == 10 and cleaned.startswith(("9", "8")):
                return "+7" + cleaned
            elif len(cleaned) == 11 and cleaned.startswith("8"):
                return "+7" + cleaned[1:]
            elif len(cleaned) == 11 and cleaned.startswith("7"):
                return "+" + cleaned
            # Белорусские номера
            elif len(cleaned) == 9 and cleaned.startswith(("29", "33", "44")):
                return "+375" + cleaned
            # Украинские номера
            elif len(cleaned) == 9 and cleaned.startswith(("50", "66", "95", "99")):
                return "+380" + cleaned

        # Если был плюс или не можем определить страну, оставляем как есть
        if has_plus and not cleaned.startswith("+"):
            cleaned = "+" + cleaned

        return cleaned

    @staticmethod
    def _is_valid_phone_universal(phone: str) -> bool:
        """Проверяет валидность телефонного номера (универсальный метод)"""

        if not phone:
            return False

        # Убираем + для проверки
        digits = phone.lstrip("+")

        if not digits:
            return False

        # Проверяем, что все символы цифры
        if not digits.isdigit():
            return False

        # Минимальная и максимальная длина для международных номеров
        # (включая код страны)
        if len(digits) < 8 or len(digits) > 15:
            return False

        # Проверка на слишком много одинаковых цифр (например, 00000000)
        if len(set(digits)) < 3:
            return False

        # Проверка на последовательности (12345678, 87654321)
        if digits in "1234567890" or digits in "0987654321":
            return False

        # Проверка на номера с большим количеством нулей
        if digits.count("0") > len(digits) * 0.7:  # Более 70% нулей
            return False

        return True
