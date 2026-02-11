import logging
import re
from typing import List, Optional, Set
from urllib.parse import urlparse

from . import constants

logger = logging.getLogger(__name__)


class PhoneValidator:
    """Универсальный класс для проверки и нормализации телефонных номеров"""

    MIN_PHONE_LENGTH = constants.MIN_PHONE_LENGTH
    MAX_PHONE_LENGTH = constants.MAX_PHONE_LENGTH
    MIN_UNIQUE_DIGITS = constants.MIN_UNIQUE_DIGITS
    MAX_REPEAT_RATIO = constants.MAX_REPEAT_RATIO
    VALID_COUNTRY_CODES = constants.VALID_COUNTRY_CODES
    NOT_PHONE_PATTERNS = constants.NOT_PHONE_PATTERNS
    SUSPICIOUS_STARTS = constants.SUSPICIOUS_STARTS
    ID_LIKE_PATTERNS = constants.ID_LIKE_PATTERNS
    DOMAIN_COUNTRY_MAP = constants.DOMAIN_COUNTRY_MAP

    @classmethod
    def _clean_phone(cls, phone: str) -> str:
        """Очищает телефон от нецифровых символов"""

        if not phone:
            return ""

        # Сохраняем плюс только если он в начале
        has_plus = phone.strip().startswith("+")

        # Удаляем все нецифровые символы
        digits = re.sub(r"[^\d]", "", phone)

        if not digits:
            return ""

        if has_plus:
            return "+" + digits
        return digits

    @classmethod
    def is_likely_phone(cls, phone: str, current_url: str = "") -> bool:
        """
        Определяет, похож ли номер на реальный телефон.
        """
        if not phone or not isinstance(phone, str):
            return False

        cleaned = cls._clean_phone(phone)
        if not cleaned:
            return False

        digits = cleaned.lstrip("+")
        has_plus = cleaned.startswith("+")

        # --- 1. БАЗОВАЯ ДЛИНА ---
        if len(digits) < 7 or len(digits) > 15:
            logger.debug(f"Phone {phone}: invalid length {len(digits)}")
            return False

        # --- 2. ЯВНЫЕ НЕ-ТЕЛЕФОНЫ ---
        for pattern_str in cls.NOT_PHONE_PATTERNS:
            if re.match(pattern_str, digits):
                logger.debug(f"Phone {phone}: matched NOT_PHONE pattern")
                return False

        # --- 3. ПОДОЗРИТЕЛЬНЫЕ НАЧАЛА ---
        if not has_plus and len(digits) >= 10:
            if any(digits.startswith(start) for start in cls.SUSPICIOUS_STARTS):
                logger.debug(f"Phone {phone}: suspicious start")
                return False

        # --- 4. УНИКАЛЬНЫЕ ЦИФРЫ ---
        if len(set(digits)) < 3:
            logger.debug(f"Phone {phone}: too few unique digits")
            return False

        # --- 5. СЛИШКОМ МНОГО НУЛЕЙ ---
        zero_ratio = digits.count("0") / len(digits)
        if zero_ratio > 0.6:
            logger.debug(f"Phone {phone}: too many zeros ({zero_ratio:.1%})")  # noqa E231
            return False

        # --- 6. ПОЛУЧАЕМ КОД СТРАНЫ ИЗ ДОМЕНА ---
        home_code = None
        if current_url:
            try:
                domain_parts = urlparse(current_url).netloc.split(".")
                if len(domain_parts) >= 2:
                    tld = domain_parts[-1].lower()
                    home_code = cls.DOMAIN_COUNTRY_MAP.get(tld)
            except Exception:
                pass

        # ========== ВАЛИДАЦИЯ МЕЖДУНАРОДНЫХ (+Х ХХХ) ==========
        if has_plus:
            country_code = None
            for code in sorted(cls.VALID_COUNTRY_CODES, key=len, reverse=True):
                if digits.startswith(code):
                    country_code = code
                    break

            if not country_code:
                logger.debug(f"Phone {phone}: invalid country code")
                return False

            # ПРОВЕРКА ДЛЯ РФ: Код города/оператора не может начинаться с 0, 1, 2
            if country_code == "7" and len(digits) > 1:
                if digits[1] in "012":
                    logger.debug(f"Phone {phone}: Russian code cannot start with {digits[1]}")
                    return False

            # ПРОВЕРКА ДЛИНЫ ПО СТРАНЕ
            if not cls._is_valid_length_for_country(digits, country_code, has_plus=True):
                logger.debug(f"Phone {phone}: invalid length {len(digits)} for country {country_code}")
                return False

            # Для .ru домена ТОЛЬКО +7
            if home_code == "7" and not digits.startswith("7"):
                logger.debug(f"Phone {phone}: not Russian format for .ru domain")
                return False

            return True

        # ========== ВАЛИДАЦИЯ ЛОКАЛЬНЫХ (БЕЗ +) ==========
        if not home_code:
            logger.debug(f"Phone {phone}: no domain context, rejecting")
            return False

        # ПРОВЕРКА ДЛИНЫ ДЛЯ ЛОКАЛЬНЫХ НОМЕРОВ
        if not cls._is_valid_length_for_country(digits, home_code, has_plus=False):
            logger.debug(f"Phone {phone}: invalid local length {len(digits)} for country {home_code}")
            return False

        # --- РОССИЯ ---
        if home_code == "7":
            if len(digits) == 10 and digits.startswith("9"):
                return True
            if len(digits) == 11 and digits[0] in "78":
                return True
            logger.debug(f"Phone {phone}: invalid Russian format")
            return False

        # --- БЕЛАРУСЬ ---
        elif home_code == "375":
            if len(digits) == 12 and digits.startswith("375"):
                return True
            if len(digits) == 9 and digits[:2] in ["25", "29", "33", "44", "17"]:
                return True
            logger.debug(f"Phone {phone}: invalid Belarusian format")
            return False

        # --- УКРАИНА ---
        elif home_code == "380":
            if len(digits) == 12 and digits.startswith("380"):
                return True
            if len(digits) == 9 and digits[:2] in [
                "50",
                "66",
                "95",
                "99",
                "67",
                "68",
                "96",
                "97",
                "98",
                "63",
                "73",
                "93",
            ]:
                return True
            logger.debug(f"Phone {phone}: invalid Ukrainian format")
            return False

        # --- США/КАНАДА ---
        elif home_code == "1":
            if len(digits) == 10:
                return True
            if len(digits) == 11 and digits.startswith("1"):
                return True
            logger.debug(f"Phone {phone}: invalid US format")
            return False

        logger.debug(f"Phone {phone}: no matching format for country code {home_code}")
        return False

    @classmethod
    def _is_valid_length_for_country(cls, digits: str, country_code: str, has_plus: bool = False) -> bool:
        """
        Проверяет, соответствует ли длина номера стандарту страны.
        """
        from . import constants

        # Получаем стандарты для страны
        standards = getattr(constants, "COUNTRY_PHONE_LENGTHS", {}).get(country_code, {})

        if not standards:
            # Если нет точных стандартов - используем общие границы
            default_min = getattr(constants, "DEFAULT_MIN_LENGTH", 8)
            default_max = getattr(constants, "DEFAULT_MAX_LENGTH", 15)
            return default_min <= len(digits) <= default_max

        valid_lengths = list(standards.values())

        if has_plus:
            return len(digits) in valid_lengths
        else:
            return len(digits) in valid_lengths

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """Проверяет последовательные цифры"""

        if len(digits) < 6:
            return False

        for i in range(len(digits) - 5):
            segment = digits[i : i + 6]
            if all(int(segment[j]) == (int(segment[0]) + j) % 10 for j in range(6)):
                return True

        for i in range(len(digits) - 5):
            segment = digits[i : i + 6]
            if all(int(segment[j]) == (int(segment[0]) - j) % 10 for j in range(6)):
                return True

        return False

    @staticmethod
    def _is_too_perfect(digits: str) -> bool:
        """Проверяет слишком 'идеальные' паттерны"""

        # Все цифры одинаковые
        if len(set(digits)) == 1:
            return True

        # Чередующиеся цифры
        if len(digits) >= 8 and len(set(digits[:2])) == 2:
            pattern = digits[:2] * (len(digits) // 2)
            if pattern == digits[: len(pattern)]:
                return True

        # Палиндромы
        if len(digits) >= 6 and digits == digits[::-1]:
            return True

        return False

    @classmethod
    def normalize_phone(cls, phone: str, current_url: str = "") -> Optional[str]:
        """
        Нормализует телефонный номер с учётом домена сайта.
        """
        if not phone:
            return None

        cleaned = cls._clean_phone(phone)
        if not cleaned:
            return None

        digits = cleaned.lstrip("+")
        has_plus = cleaned.startswith("+")

        # Проверка длины
        if len(digits) < 7 or len(digits) > 15:
            return None

        # Получаем код страны из домена
        home_code = None
        if current_url:
            try:
                domain_parts = urlparse(current_url).netloc.split(".")
                if len(domain_parts) >= 2:
                    tld = domain_parts[-1].lower()
                    home_code = cls.DOMAIN_COUNTRY_MAP.get(tld)
            except Exception:
                pass

        if has_plus:
            # Проверяем код страны
            country_code = None
            for code in sorted(cls.VALID_COUNTRY_CODES, key=len, reverse=True):
                if digits.startswith(code):
                    country_code = code
                    break

            if not country_code:
                return None

            if not cls._is_valid_length_for_country(digits, country_code, has_plus=True):
                return None

            return cleaned

        if not home_code:
            return None

        if not cls._is_valid_length_for_country(digits, home_code, has_plus=False):
            return None

        # Россия
        if home_code == "7":
            if len(digits) == 10 and digits.startswith("9"):
                return "+7" + digits
            if len(digits) == 11 and digits.startswith("8"):
                return "+7" + digits[1:]
            if len(digits) == 11 and digits.startswith("7"):
                return "+" + digits
            return None

        # Беларусь
        if home_code == "375":
            if len(digits) == 12 and digits.startswith("375"):
                return "+" + digits
            if len(digits) == 9 and digits[:2] in ["25", "29", "33", "44", "17"]:
                return "+375" + digits
            if len(digits) == 12 and digits.startswith("375"):
                return "+" + digits
            return None

        # Украина
        if home_code == "380":
            if len(digits) == 12 and digits.startswith("380"):
                return "+" + digits
            if len(digits) == 9:
                return "+380" + digits
            return None

        # США
        if home_code == "1":
            if len(digits) == 10:
                return "+1" + digits
            if len(digits) == 11 and digits.startswith("1"):
                return "+" + digits
            return None

        return None

    @classmethod
    def validate_and_normalize_phones(cls, phones: Set[str], current_url: str = "") -> List[str]:
        """
        Валидирует и нормализует набор телефонных номеров.
        """
        valid_phones = set()

        for phone in phones:
            normalized = cls.normalize_phone(phone, current_url)
            if normalized and cls.is_likely_phone(normalized, current_url):
                valid_phones.add(normalized)
                logger.debug(f"Valid phone: {phone} -> {normalized}")
            else:
                logger.debug(f"Invalid phone: {phone}")

        return sorted(list(valid_phones))


class EmailValidator:
    """Класс для валидации email адресов"""

    try:
        KNOWN_GOOD_DOMAINS = constants.KNOWN_GOOD_EMAIL_DOMAINS
    except AttributeError:
        logger.warning("constants.KNOWN_GOOD_EMAIL_DOMAINS не найдена, использую базовый набор")
        KNOWN_GOOD_DOMAINS = {
            "gmail.com",
            "mail.ru",
            "yandex.ru",
            "outlook.com",
            "hotmail.com",
            "yahoo.com",
            "protonmail.com",
            "icloud.com",
        }

    try:
        BAD_DOMAINS = constants.BAD_EMAIL_DOMAINS
    except AttributeError:
        # Если константы нет - создаём базовую
        logger.warning("constants.BAD_EMAIL_DOMAINS не найдена, использую базовый набор")
        BAD_DOMAINS = {"example.com", "example.ru", "test.com", "test.ru", "domain.com", "localhost", "invalid.com"}

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Проверяет валидность email"""

        if not email or "@" not in email:
            return False

        email = email.lower().strip()
        try:
            local_part, domain = email.split("@", 1)
        except ValueError:
            return False

        # Базовая проверка длины
        if len(local_part) > 64 or len(domain) > 255:
            return False

        # Проверка домена
        if "." not in domain:
            return False
        if domain.startswith(".") or domain.endswith("."):
            return False

        # Проверка на тестовые домены
        if domain in cls.BAD_DOMAINS:
            return False

        # Проверка формата
        if not re.match(r"^[a-zA-Z0-9._%+-]+$", local_part):
            return False
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
            return False

        return True

    @classmethod
    def normalize_email(cls, email: str) -> str:
        """Нормализует email"""

        if not email:
            return ""
        return email.lower().strip()

    @classmethod
    def validate_and_normalize_emails(cls, emails: Set[str]) -> List[str]:
        """Валидирует и нормализует набор email адресов"""

        valid_emails = set()

        for email in emails:
            if not email:
                continue
            normalized = cls.normalize_email(email)
            if cls.is_valid_email(normalized):
                valid_emails.add(normalized)

        return sorted(list(valid_emails))
