from unittest.mock import patch

import pytest

from contact_parser import constants
from contact_parser.validators import EmailValidator, PhoneValidator


class TestPhoneValidator:
    """Базовые тесты для PhoneValidator"""

    def test_clean_phone(self):
        """Тест очистки телефонного номера"""

        assert PhoneValidator._clean_phone("+7 (999) 123-45-67") == "+79991234567"
        assert PhoneValidator._clean_phone("8-916-123-45-67") == "89161234567"
        assert PhoneValidator._clean_phone("") == ""
        assert PhoneValidator._clean_phone("abc") == ""
        assert PhoneValidator._clean_phone("+1+2+3") == "+123"

    def test_is_likely_phone_russian(self):
        """Тест российских номеров"""

        assert PhoneValidator.is_likely_phone("+79991234567", "https://example.ru") is True
        assert PhoneValidator.is_likely_phone("89161234567", "https://example.ru") is True
        assert PhoneValidator.is_likely_phone("9161234567", "https://example.ru") is True
        assert PhoneValidator.is_likely_phone("+71589871646", "https://example.ru") is False

    def test_is_likely_phone_belarusian(self):
        """Тест белорусских номеров"""

        assert PhoneValidator.is_likely_phone("+375291234567", "https://example.by") is True
        assert PhoneValidator.is_likely_phone("291234567", "https://example.by") is True
        assert PhoneValidator.is_likely_phone("375291234567", "https://example.by") is True
        assert PhoneValidator.is_likely_phone("+37599999999", "https://example.by") is False

    def test_is_likely_phone_us(self):
        """Тест американских номеров"""

        assert PhoneValidator.is_likely_phone("+15551234567", "https://example.com") is True
        assert PhoneValidator.is_likely_phone("5551234567", "https://example.com") is True
        assert PhoneValidator.is_likely_phone("15551234567", "https://example.com") is True
        assert PhoneValidator.is_likely_phone("555123456", "https://example.com") is False

    def test_normalize_phone_russian(self):
        """Тест нормализации российских номеров"""

        assert PhoneValidator.normalize_phone("+7 (999) 123-45-67", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("8(999)1234567", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("9991234567", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("9991234567") is None

    def test_normalize_phone_belarusian(self):
        """Тест нормализации белорусских номеров"""

        assert PhoneValidator.normalize_phone("+375 29 616-77-77", "https://example.by") == "+375296167777"
        assert PhoneValidator.normalize_phone("291234567", "https://example.by") == "+375291234567"
        assert PhoneValidator.normalize_phone("375291234567", "https://example.by") == "+375291234567"

    def test_normalize_phone_us(self):
        """Тест нормализации американских номеров"""

        assert PhoneValidator.normalize_phone("5551234567", "https://example.com") == "+15551234567"
        assert PhoneValidator.normalize_phone("15551234567", "https://example.com") == "+15551234567"
        assert PhoneValidator.normalize_phone("+15551234567", "https://example.com") == "+15551234567"

    def test_clean_phone_none(self):
        """Тест очистки None"""

        assert PhoneValidator._clean_phone(None) == ""


class TestPhoneValidatorAdvanced:
    """Расширенные тесты для PhoneValidator"""

    def test_is_sequential_all_patterns(self):
        """Тест всех последовательных паттернов"""

        ascending = ["123456", "234567", "345678", "456789", "567890"]
        descending = ["098765", "987654", "876543", "765432", "654321"]

        for pattern in ascending + descending:
            assert PhoneValidator._is_sequential(pattern) is True

        assert PhoneValidator._is_sequential("12345") is False
        assert PhoneValidator._is_sequential("123459") is False
        assert PhoneValidator._is_sequential("111111") is False

    def test_is_too_perfect_all_patterns(self):
        """Тест всех 'идеальных' паттернов"""

        assert PhoneValidator._is_too_perfect("12121212") is True
        assert PhoneValidator._is_too_perfect("34343434") is True
        assert PhoneValidator._is_too_perfect("123321") is True
        assert PhoneValidator._is_too_perfect("1234554321") is True
        assert PhoneValidator._is_too_perfect("111111") is True
        assert PhoneValidator._is_too_perfect("9161234567") is False

    def test_is_valid_length_for_country(self):
        """Тест проверки длины по стандарту страны"""
        # Россия
        assert PhoneValidator._is_valid_length_for_country("79991234567", "7", has_plus=True) is True
        assert PhoneValidator._is_valid_length_for_country("9161234567", "7", has_plus=False) is True
        assert PhoneValidator._is_valid_length_for_country("999123456", "7", has_plus=False) is False

        # Беларусь
        assert PhoneValidator._is_valid_length_for_country("375291234567", "375", has_plus=True) is True
        assert PhoneValidator._is_valid_length_for_country("291234567", "375", has_plus=False) is True
        assert PhoneValidator._is_valid_length_for_country("37599999999", "375", has_plus=True) is False

        # Неизвестная страна (покрывает строки 403, 414, 425)
        original_min = constants.DEFAULT_MIN_LENGTH
        original_max = constants.DEFAULT_MAX_LENGTH
        constants.DEFAULT_MIN_LENGTH = 8
        constants.DEFAULT_MAX_LENGTH = 15

        assert PhoneValidator._is_valid_length_for_country("12345678", "999") is True
        assert PhoneValidator._is_valid_length_for_country("1234567", "999") is False
        assert PhoneValidator._is_valid_length_for_country("1" * 16, "999") is False

        constants.DEFAULT_MIN_LENGTH = original_min
        constants.DEFAULT_MAX_LENGTH = original_max

    def test_validate_and_normalize_phones(self):
        """Тест валидации и нормализации набора телефонов"""

        phones = {
            "+7 (999) 123-45-67",
            "8(916)1234567",
            "+375291234567",
            "invalid",
        }
        result = PhoneValidator.validate_and_normalize_phones(phones, "https://example.ru")
        assert len(result) == 2
        assert all(p.startswith("+7") for p in result)


class TestEmailValidator:
    """Тесты для EmailValidator"""

    def test_is_valid_email_valid(self):
        """Тест валидных email"""

        assert EmailValidator.is_valid_email("test@gmail.com") is True
        assert EmailValidator.is_valid_email("user.name@company.co.uk") is True
        assert EmailValidator.is_valid_email("test+filter@gmail.com") is True
        assert EmailValidator.is_valid_email("user_name@my-work-domain.com") is True

    def test_is_valid_email_invalid(self):
        """Тест невалидных email"""

        assert EmailValidator.is_valid_email("test@com") is False
        assert EmailValidator.is_valid_email("@example.com") is False
        assert EmailValidator.is_valid_email("test@.com") is False
        assert EmailValidator.is_valid_email("test!@domain.com") is False

    def test_bad_domains_filter(self):
        """Тест фильтрации плохих доменов"""

        assert EmailValidator.is_valid_email("test@example.com") is False
        assert EmailValidator.is_valid_email("test@test.ru") is False
        assert EmailValidator.is_valid_email("test@localhost") is False

    def test_normalize_email(self):
        """Тест нормализации email"""

        assert EmailValidator.normalize_email("  TEST@GMAIL.COM  ") == "test@gmail.com"
        assert EmailValidator.normalize_email("User@Site.ORG") == "user@site.org"
        assert EmailValidator.normalize_email("") == ""

    def test_validate_and_normalize_emails(self):
        """Тест валидации и нормализации набора email"""

        emails = {
            "  TEST@GMAIL.COM  ",
            "user_name@work-mail.com",
            "invalid@com",
            "test@example.com",
        }
        result = EmailValidator.validate_and_normalize_emails(emails)
        assert "test@gmail.com" in result
        assert "user_name@work-mail.com" in result
        assert "test@example.com" not in result

    def test_email_underscore_specific(self):
        """Специфический тест для email с подчёркиванием"""

        assert EmailValidator.is_valid_email("user_name@work-mail.com") is True
        assert EmailValidator.is_valid_email("my_name@test.co.uk") is True
        assert EmailValidator.is_valid_email("first_last@gmail.com") is True


class TestPhoneValidatorCountrySpecific:
    """Тесты для специфичной валидации по странам"""

    @pytest.mark.parametrize(
        "phone,url,expected",
        [
            # Россия
            ("+79991234567", "https://example.ru", True),
            ("89161234567", "https://example.ru", True),
            ("9161234567", "https://example.ru", True),
            ("+71589871646", "https://example.ru", False),
            # Беларусь
            ("+375291234567", "https://example.by", True),
            ("291234567", "https://example.by", True),
            ("375291234567", "https://example.by", True),
            ("+37599999999", "https://example.by", False),
            # США
            ("+15551234567", "https://example.com", True),
            ("5551234567", "https://example.com", True),
            ("15551234567", "https://example.com", True),
        ],
    )
    def test_country_specific_validation(self, phone, url, expected):
        assert PhoneValidator.is_likely_phone(phone, url) is expected

    def test_domain_country_mapping(self):
        """Тест маппинга доменов в коды стран"""

        assert constants.DOMAIN_COUNTRY_MAP.get("ru") == "7"
        assert constants.DOMAIN_COUNTRY_MAP.get("by") == "375"
        assert constants.DOMAIN_COUNTRY_MAP.get("com") == "1"

    def test_clean_phone_empty_edge(self):
        """Тест очистки пустого телефона"""

        assert PhoneValidator._clean_phone("   ") == ""
        assert PhoneValidator._clean_phone(None) == ""

    def test_is_likely_phone_debug_logging(self):
        """Тест debug логирования при валидации"""

        with patch("contact_parser.validators.logger") as mock_logger:
            PhoneValidator.is_likely_phone("123", "https://example.ru")
            mock_logger.debug.assert_called()

            PhoneValidator.is_likely_phone("12345678", "https://example.ru")
            mock_logger.debug.assert_called()

            PhoneValidator.is_likely_phone("4941234567", "https://example.ru")
            mock_logger.debug.assert_called()

    def test_is_likely_phone_all_debug_logs(self):
        """Тест ВСЕХ debug логов в is_likely_phone"""

        with patch("contact_parser.validators.logger") as mock_logger:
            PhoneValidator.is_likely_phone("123")
            mock_logger.debug.assert_any_call("Phone 123: invalid length 3")

            PhoneValidator.is_likely_phone("12345678")
            mock_logger.debug.assert_any_call("Phone 12345678: matched NOT_PHONE pattern")

            PhoneValidator.is_likely_phone("4941234567", "https://example.ru")
            mock_logger.debug.assert_any_call("Phone 4941234567: suspicious start")

            PhoneValidator.is_likely_phone("11111111", "https://example.ru")
            mock_logger.debug.assert_any_call("Phone 11111111: matched NOT_PHONE pattern")

    def test_ukrainian_codes_comprehensive(self):
        """Тест всех украинских кодов операторов"""

        codes = ["50", "66", "95", "99", "67", "68", "96", "97", "98", "63", "73", "93"]
        for code in codes:
            phone = f"{code}1234567"
            assert PhoneValidator.is_likely_phone(phone, "https://example.ua") is True

    def test_us_phone_invalid_logging(self):
        """Тест логирования невалидного US номера"""

        with patch("contact_parser.validators.logger") as mock_logger:
            PhoneValidator.is_likely_phone("555123456", "https://example.com")
            mock_logger.debug.assert_called_with("Phone 555123456: invalid local length 9 for country 1")

    def test_is_sequential_all_combinations(self):
        """Тест всех комбинаций последовательных цифр"""

        for start in range(0, 5):
            seq = "".join(str((start + i) % 10) for i in range(6))
            assert PhoneValidator._is_sequential(seq) is True

        for start in range(9, 4, -1):
            seq = "".join(str((start - i) % 10) for i in range(6))
            assert PhoneValidator._is_sequential(seq) is True

        assert PhoneValidator._is_sequential("12345") is False

    def test_normalize_phone_russian_all_variants(self):
        """Тест всех вариантов российских номеров"""

        assert PhoneValidator.normalize_phone("+7 (999) 123-45-67", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("8(999)1234567", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("9991234567", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("7(999)1234567", "https://example.ru") == "+79991234567"
        assert PhoneValidator.normalize_phone("88001234567", "https://example.ru") == "+78001234567"

    def test_bad_domains_fallback(self):
        """Тест fallback BAD_DOMAINS при отсутствии константы"""

        with patch("contact_parser.validators.constants") as mock_constants:
            delattr(mock_constants, "BAD_EMAIL_DOMAINS")  # Удаляем атрибут
            from contact_parser.validators import EmailValidator

            validator = EmailValidator()
            assert "example.com" in validator.BAD_DOMAINS

    def test_normalize_email_edge_cases(self):
        """Тест normalize_email с граничными случаями"""

        assert EmailValidator.normalize_email(None) == ""
        assert EmailValidator.normalize_email("   ") == ""
        assert EmailValidator.normalize_email("  TEST  ") == "test"

    def test_validate_and_normalize_emails_empty(self):
        """Тест валидации пустого набора email"""

        assert EmailValidator.validate_and_normalize_emails(set()) == []
        assert EmailValidator.validate_and_normalize_emails({""}) == []

    def test_is_valid_length_for_country_all_countries(self):
        """Тест проверки длины для всех стран из COUNTRY_PHONE_LENGTHS"""

        from contact_parser.constants import COUNTRY_PHONE_LENGTHS

        for country_code, standards in COUNTRY_PHONE_LENGTHS.items():
            for length_name, length in standards.items():
                digits = "1" * length
                assert PhoneValidator._is_valid_length_for_country(digits, country_code, True) is True

                assert PhoneValidator._is_valid_length_for_country(digits, country_code, True) is True
                assert PhoneValidator._is_valid_length_for_country(digits, country_code, False) is True

    def test_is_too_perfect_all_patterns(self):
        """Тест всех 'идеальных' паттернов"""

        # Чередующиеся
        assert PhoneValidator._is_too_perfect("12121212") is True
        assert PhoneValidator._is_too_perfect("34343434") is True
        assert PhoneValidator._is_too_perfect("56565656") is True

        # Палиндромы
        assert PhoneValidator._is_too_perfect("123321") is True
        assert PhoneValidator._is_too_perfect("1234554321") is True
        assert PhoneValidator._is_too_perfect("123454321") is True

        # Одинаковые
        assert PhoneValidator._is_too_perfect("111111") is True
        assert PhoneValidator._is_too_perfect("22222222") is True

        # Не подходят
        assert PhoneValidator._is_too_perfect("9161234567") is False
        assert PhoneValidator._is_too_perfect("1234567890") is False

    def test_validate_and_normalize_phones_empty(self):
        """Тест валидации пустого набора телефонов"""

        assert PhoneValidator.validate_and_normalize_phones(set(), "https://example.ru") == []
        assert PhoneValidator.validate_and_normalize_phones({""}, "https://example.ru") == []
        assert PhoneValidator.validate_and_normalize_phones(set(), "https://example.ru") == []

    def test_ukrainian_codes_all(self):
        """Тест ВСЕХ украинских кодов операторов"""

        codes = ["50", "66", "95", "99", "67", "68", "96", "97", "98", "63", "73", "93"]
        for code in codes:
            phone = f"{code}1234567"
            assert PhoneValidator.is_likely_phone(phone, "https://example.ua") is True

    def test_us_phone_invalid_format_logging(self):
        """Тест логирования невалидного US формата"""

        with patch("contact_parser.validators.logger") as mock_logger:
            PhoneValidator.is_likely_phone("555123456", "https://example.com")
            mock_logger.debug.assert_called_with("Phone 555123456: invalid local length 9 for country 1")

    def test_is_sequential_full_coverage(self):
        """Тест 100% покрытия _is_sequential"""

        for start in range(0, 5):
            seq = "".join(str((start + i) % 10) for i in range(6))
            assert PhoneValidator._is_sequential(seq) is True

        for start in range(9, 4, -1):
            seq = "".join(str((start - i) % 10) for i in range(6))
            assert PhoneValidator._is_sequential(seq) is True

        assert PhoneValidator._is_sequential("12345") is False

    def test_normalize_phone_russian_complete(self):
        """Тест ВСЕХ вариантов нормализации РФ"""
        test_cases = [
            ("+7 (999) 123-45-67", "+79991234567"),
            ("8(999)1234567", "+79991234567"),
            ("9991234567", "+79991234567"),
            ("7(999)1234567", "+79991234567"),
            ("88001234567", "+78001234567"),
        ]
        for input_phone, expected in test_cases:
            assert PhoneValidator.normalize_phone(input_phone, "https://example.ru") == expected

    def test_bad_domains_fallback_full(self):
        """Тест fallback BAD_DOMAINS при импорте"""

        with patch("contact_parser.validators.constants") as mock_const:
            del mock_const.BAD_EMAIL_DOMAINS

            import importlib

            from contact_parser import validators

            importlib.reload(validators)

            assert "example.com" in validators.EmailValidator.BAD_DOMAINS

    def test_normalize_email_edge_cases_complete(self):
        """Тест normalize_email с граничными случаями"""

        assert EmailValidator.normalize_email(None) == ""
        assert EmailValidator.normalize_email("   ") == ""
        assert EmailValidator.normalize_email("") == ""

    def test_validate_and_normalize_emails_empty_set(self):
        """Тест валидации пустого набора email"""

        assert EmailValidator.validate_and_normalize_emails(set()) == []
        assert EmailValidator.validate_and_normalize_emails({""}) == []
        assert EmailValidator.validate_and_normalize_emails({"", None}) == []

    def test_is_too_perfect_complete(self):
        """Тест 100% покрытия _is_too_perfect"""
        assert PhoneValidator._is_too_perfect("12121212") is True
        assert PhoneValidator._is_too_perfect("34343434") is True

        assert PhoneValidator._is_too_perfect("123321") is True
        assert PhoneValidator._is_too_perfect("1234554321") is True

        assert PhoneValidator._is_too_perfect("111111") is True
