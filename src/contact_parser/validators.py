import logging
import re
from typing import List, Optional, Set

try:
    import phonenumbers

    HAS_PHONENUMBERS = True
except ImportError:
    HAS_PHONENUMBERS = False
    logging.warning("phonenumbers library not installed. Using simple validation.")

logger = logging.getLogger(__name__)


class PhoneValidator:
    """Универсальный класс для проверки и нормализации телефонных номеров"""

    # TODO: Константы для настройки валидации (сбалансированные)
    MIN_PHONE_LENGTH = 7  # Минимальная длина телефона (с кодом страны)
    MAX_PHONE_LENGTH = 15  # Максимальная длина телефона (с кодом страны)
    MIN_UNIQUE_DIGITS = 3  # Минимум уникальных цифр в номере (уменьшили)
    MAX_REPEAT_RATIO = 0.7  # Максимум 70% одинаковых цифр (увеличили)

    # TODO: Список известных кодов стран (для быстрой проверки)
    VALID_COUNTRY_CODES = {
        "1",
        "7",
        "20",
        "27",
        "30",
        "31",
        "32",
        "33",
        "34",
        "36",
        "39",
        "40",
        "41",
        "43",
        "44",
        "45",
        "46",
        "47",
        "48",
        "49",
        "51",
        "52",
        "53",
        "54",
        "55",
        "56",
        "57",
        "58",
        "60",
        "61",
        "62",
        "63",
        "64",
        "65",
        "66",
        "81",
        "82",
        "84",
        "86",
        "90",
        "91",
        "92",
        "93",
        "94",
        "95",
        "98",
        "211",
        "212",
        "213",
        "216",
        "218",
        "220",
        "221",
        "222",
        "223",
        "224",
        "225",
        "226",
        "227",
        "228",
        "229",
        "230",
        "231",
        "232",
        "233",
        "234",
        "235",
        "236",
        "237",
        "238",
        "239",
        "240",
        "241",
        "242",
        "243",
        "244",
        "245",
        "246",
        "247",
        "248",
        "249",
        "250",
        "251",
        "252",
        "253",
        "254",
        "255",
        "256",
        "257",
        "258",
        "259",
        "260",
        "261",
        "262",
        "263",
        "264",
        "265",
        "266",
        "267",
        "268",
        "269",
        "290",
        "291",
        "297",
        "298",
        "299",
        "350",
        "351",
        "352",
        "353",
        "354",
        "355",
        "356",
        "357",
        "358",
        "359",
        "370",
        "371",
        "372",
        "373",
        "374",
        "375",
        "376",
        "377",
        "378",
        "379",
        "380",
        "381",
        "382",
        "383",
        "385",
        "386",
        "387",
        "389",
        "420",
        "421",
        "423",
        "500",
        "501",
        "502",
        "503",
        "504",
        "505",
        "506",
        "507",
        "508",
        "509",
        "590",
        "591",
        "592",
        "593",
        "594",
        "595",
        "596",
        "597",
        "598",
        "599",
        "670",
        "672",
        "673",
        "674",
        "675",
        "676",
        "677",
        "678",
        "679",
        "680",
        "681",
        "682",
        "683",
        "685",
        "686",
        "687",
        "688",
        "689",
        "690",
        "691",
        "692",
        "850",
        "852",
        "853",
        "855",
        "856",
        "880",
        "886",
        "960",
        "961",
        "962",
        "963",
        "964",
        "965",
        "966",
        "967",
        "968",
        "970",
        "971",
        "972",
        "973",
        "974",
        "975",
        "976",
        "977",
        "992",
        "993",
        "994",
        "995",
        "996",
        "998",
    }

    # TODO: Паттерны, которые точно НЕ телефоны (внутренние ID и т.д.)
    NOT_PHONE_PATTERNS = [
        # Слишком короткие
        r"^\d{1,5}$",
        # Слишком длинные
        r"^\d{16,}$",
        # Одинаковые цифры (6+ одинаковых)
        r"^(\d)\1{5,}$",
        # Последовательности (6+ подряд)
        r"^123456\d*$",
        r"^234567\d*$",
        r"^345678\d*$",
        r"^456789\d*$",
        r"^567890\d*$",
        r"^098765\d*$",
        r"^987654\d*$",
        r"^876543\d*$",
        r"^765432\d*$",
        r"^654321\d*$",
        # Двоичные
        r"^[01]+$",
    ]

    # TODO: Подозрительные начала номеров (часто ID товаров)
    SUSPICIOUS_STARTS = ["494", "443", "475", "476", "172", "173"]

    @classmethod
    def _clean_phone(cls, phone: str) -> str:
        """Очищает телефон от нецифровых символов"""
        if not phone:
            return ""

        # Сохраняем плюс в начале
        has_plus = phone.startswith("+")
        cleaned = re.sub(r"[^\d+]", "", phone)

        # Убираем плюсы из середины строки
        if "+" in cleaned[1:]:
            cleaned = cleaned[0] + cleaned[1:].replace("+", "")

        # Возвращаем плюс если он был изначально
        if has_plus and not cleaned.startswith("+"):
            cleaned = "+" + cleaned

        return cleaned

    @classmethod
    def is_likely_phone(cls, phone: str) -> bool:
        """УНИВЕРСАЛЬНЫЙ метод определения похожести на телефон"""
        if not phone or not isinstance(phone, str):
            return False

        # TODO: 1. Очистка
        cleaned = cls._clean_phone(phone)

        if not cleaned:
            return False

        digits = cleaned.lstrip("+")

        # TODO: 2. Проверка длины
        if len(digits) < cls.MIN_PHONE_LENGTH or len(digits) > cls.MAX_PHONE_LENGTH:
            logger.debug(f"Phone {phone} rejected: invalid length {len(digits)}")
            return False

        # TODO: 3. Проверка что все символы цифры
        if not digits.isdigit():
            logger.debug(f"Phone {phone} rejected: contains non-digits")
            return False

        # TODO: 4. Проверка на заведомо не телефонные паттерны
        for pattern in cls.NOT_PHONE_PATTERNS:
            if re.match(pattern, digits):
                logger.debug(f"Phone {phone} rejected: matches not-phone pattern {pattern}")
                return False

        # TODO: 5. Проверка на подозрительные начала (ID товаров)
        for start in cls.SUSPICIOUS_STARTS:
            if digits.startswith(start):
                logger.debug(f"Phone {phone} rejected: starts with suspicious pattern {start}")
                return False

        # TODO: 6. Проверка уникальности цифр
        unique_digits = len(set(digits))
        if unique_digits < cls.MIN_UNIQUE_DIGITS:
            logger.debug(f"Phone {phone} rejected: only {unique_digits} unique digits")
            return False

        # TODO: 7. Проверка на слишком много одинаковых цифр
        max_repeat_count = max(digits.count(d) for d in set(digits))
        if max_repeat_count / len(digits) > cls.MAX_REPEAT_RATIO:
            logger.debug(f"Phone {phone} rejected: {max_repeat_count}/{len(digits)} repeating digits")
            return False

        # TODO: 8. Проверка на последовательности (только для длинных)
        if len(digits) >= 8 and cls._is_sequential(digits):
            logger.debug(f"Phone {phone} rejected: sequential digits")
            return False

        # TODO: 9. Проверка на "красивые" паттерны
        if cls._is_too_perfect(digits):
            logger.debug(f"Phone {phone} rejected: too perfect pattern")
            return False

        # TODO: 10. Если номер с +, проверяем код страны
        if cleaned.startswith("+"):
            # Извлекаем возможные коды стран (1-3 цифры)
            for i in range(1, min(4, len(digits)) + 1):
                country_code = digits[:i]
                if country_code in cls.VALID_COUNTRY_CODES:
                    # Нашли валидный код страны
                    remaining_digits = digits[i:]

                    # Проверяем длину номера после кода страны
                    if 6 <= len(remaining_digits) <= 14:  # Реальные номера 6-14 цифр
                        logger.debug(f"Phone {phone} accepted: valid country code {country_code}")
                        return True

            # Если код страны не найден, но номер выглядит нормально
            if 8 <= len(digits) <= 14:
                logger.debug(f"Phone {phone} accepted: international format without known country code")
                return True

            logger.debug(f"Phone {phone} rejected: invalid international format")
            return False
        else:
            # TODO: 11. Проверка локальных номеров (без +)
            # Локальные номера должны иметь разумную длину
            if 7 <= len(digits) <= 12:
                # Дополнительные проверки для локальных номеров
                if cls._is_valid_local_number(digits):
                    logger.debug(f"Phone {phone} accepted: valid local number")
                    return True

        logger.debug(f"Phone {phone} rejected: doesn't match any phone pattern")
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """Проверяет последовательные цифры (только явные последовательности)"""
        if len(digits) < 6:
            return False

        # Проверка возрастающей последовательности (123456, 234567 и т.д.)
        for i in range(len(digits) - 5):
            segment = digits[i : i + 6]
            if all(int(segment[j]) == (int(segment[0]) + j) % 10 for j in range(6)):
                return True

        # Проверка убывающей последовательности (654321, 543210 и т.д.)
        for i in range(len(digits) - 5):
            segment = digits[i : i + 6]
            if all(int(segment[j]) == (int(segment[0]) - j) % 10 for j in range(6)):
                return True

        return False

    @staticmethod
    def _is_too_perfect(digits: str) -> bool:
        """Проверяет слишком 'идеальные' паттерны"""
        # Все цифры одинаковые (уже проверено выше)
        if len(set(digits)) == 1:
            return True

        # Чередующиеся цифры (12121212, 34343434)
        if len(digits) >= 8:
            # Паттерн из 2 цифр
            if len(set(digits[:2])) == 2 and digits[:2] * (len(digits) // 2) == digits[: len(digits) // 2 * 2]:
                return True

        # Симметричные номера (123321, 1234554321)
        if len(digits) >= 6:
            # Полная симметрия
            if digits == digits[::-1]:
                return True
            # Центральная симметрия для четной длины
            if len(digits) % 2 == 0:
                half = len(digits) // 2
                if digits[:half] == digits[half:][::-1]:
                    return True

        return False

    @staticmethod
    def _is_valid_local_number(digits: str) -> bool:
        """Проверяет валидность локального номера (без кода страны)"""
        # Не должен начинаться с 0 (обычно)
        if digits[0] == "0":
            return False

        # Проверяем что номер не состоит из малого набора цифр
        digit_set = set(digits)
        if len(digit_set) < 3:  # Слишком мало уникальных цифр
            return False

        # Не должен быть "плохим" паттерном
        bad_local_patterns = [
            r"^\d{8}$",  # Ровно 8 цифр часто ID
            r"^\d{10}$",  # Ровно 10 цифр тоже подозрительно
        ]

        for pattern in bad_local_patterns:
            if re.match(pattern, digits) and len(set(digits)) < 4:
                return False

        return True

    @classmethod
    def normalize_phone(cls, phone: str) -> Optional[str]:
        """
        Нормализует телефон к международному формату
        Возвращает None если номер невалиден
        """
        if not phone:
            return None

        # TODO: 1. Проверяем похожесть на телефон
        if not cls.is_likely_phone(phone):
            logger.debug(f"Phone {phone} rejected: not likely a phone number")
            return None

        cleaned = cls._clean_phone(phone)

        # TODO: 2. Используем phonenumbers если доступно
        if HAS_PHONENUMBERS:
            try:
                # Пробуем разные регионы
                regions = [None] + [
                    "US",
                    "GB",
                    "RU",
                    "BY",
                    "UA",
                    "DE",
                    "FR",
                    "CN",
                    "JP",
                ]
                for region in regions:
                    try:
                        parsed = phonenumbers.parse(cleaned, region)
                        if phonenumbers.is_valid_number(parsed):
                            normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                            logger.debug(f"Phone {phone} normalized to {normalized}")
                            return normalized
                    except Exception:
                        continue
            except Exception as e:
                logger.warning(f"Error normalizing phone {phone} with phonenumbers: {e}")

        # TODO: 3. Простая нормализация если phonenumbers не доступен
        digits = cleaned.lstrip("+")

        # Если уже с +, возвращаем как есть
        if cleaned.startswith("+"):
            return cleaned

        # TODO: 4. Попробуем определить страну
        # Российские/Казахстанские
        if len(digits) == 10 and digits[0] in ["7", "8", "9"]:
            return "+7" + digits
        elif len(digits) == 11 and digits.startswith("8"):
            return "+7" + digits[1:]
        elif len(digits) == 11 and digits.startswith("7"):
            return "+" + digits

        # Белорусские
        if len(digits) == 9 and digits[:2] in ["25", "29", "33", "44"]:
            return "+375" + digits
        elif len(digits) == 12 and digits.startswith("375"):
            return "+" + digits

        # Украинские
        if len(digits) == 9 and digits[:2] in [
            "50",
            "66",
            "95",
            "99",
            "63",
            "73",
            "93",
        ]:
            return "+380" + digits
        elif len(digits) == 12 and digits.startswith("380"):
            return "+" + digits

        # TODO: 5. Общий случай - добавляем + если номер валидный
        if 7 <= len(digits) <= 12:
            return "+" + digits

        logger.debug(f"Phone {phone} could not be normalized")
        return None

    @classmethod
    def validate_and_normalize_phones(cls, phones: Set[str]) -> List[str]:
        """
        Валидирует и нормализует набор телефонных номеров
        Возвращает отсортированный список уникальных нормализованных номеров
        """
        valid_phones = set()

        for phone in phones:
            normalized = cls.normalize_phone(phone)
            if normalized:
                # Двойная проверка после нормализации
                if cls.is_likely_phone(normalized):
                    valid_phones.add(normalized)
                else:
                    logger.debug(f"Phone {phone} -> {normalized} failed final validation")

        return sorted(list(valid_phones))


class EmailValidator:
    """Класс для валидации email адресов"""

    # Паттерны для фильтрации плохих email
    BAD_DOMAINS = {
        "example.com",
        "example.ru",
        "example.org",
        "test.com",
        "test.ru",
        "test.org",
        "domain.com",
        "domain.ru",
        "domain.org",
        "email.com",
        "email.ru",
        "email.org",
        "site.com",
        "site.ru",
        "site.org",
        "yoursite.com",
        "yourdomain.com",
    }

    @classmethod
    def is_valid_email(cls, email: str) -> bool:
        """Проверяет валидность email"""
        if not email or "@" not in email:
            return False

        local_part, domain = email.split("@", 1)

        # Проверка длины
        if len(local_part) > 64 or len(domain) > 255:
            return False

        # Проверка наличия точки в домене
        if "." not in domain:
            return False

        # Проверка что домен не начинается и не заканчивается точкой
        if domain.startswith(".") or domain.endswith("."):
            return False

        # Проверка на плохие домены
        if domain.lower() in cls.BAD_DOMAINS:
            return False

        # Проверка валидных символов в local part
        if not re.match(r"^[a-zA-Z0-9._%+-]+$", local_part):
            return False

        # Проверка валидных символов в domain
        if not re.match(r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", domain):
            return False

        return True

    @classmethod
    def normalize_email(cls, email: str) -> str:
        """Нормализует email (нижний регистр, обрезает пробелы)"""

        return email.lower().strip()

    @classmethod
    def validate_and_normalize_emails(cls, emails: Set[str]) -> List[str]:
        """Валидирует и нормализует набор email адресов"""

        valid_emails = set()

        for email in emails:
            normalized = cls.normalize_email(email)
            if cls.is_valid_email(normalized):
                valid_emails.add(normalized)

        return sorted(list(valid_emails))
