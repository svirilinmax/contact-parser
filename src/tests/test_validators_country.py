import pytest

from contact_parser.validators import PhoneValidator


class TestPhoneValidatorCountrySpecific:
    """Тесты для специфичной валидации по странам"""

    @pytest.mark.parametrize(
        "phone,url,expected",
        [
            # Россия
            ("+79991234567", "https://example.ru", True),
            ("89161234567", "https://example.ru", True),
            ("9161234567", "https://example.ru", True),
            ("+77123456789", "https://example.kz", True),
            ("+71589871646", "https://example.ru", False),  # Невалидный код
            # Беларусь
            ("+375291234567", "https://example.by", True),
            ("291234567", "https://example.by", True),
            ("375291234567", "https://example.by", True),
            ("+37599999999", "https://example.by", False),  # 11 цифр
            # Украина
            ("+380501234567", "https://example.ua", True),
            ("501234567", "https://example.ua", True),
            ("+380631234567", "https://example.ua", True),
            # США
            ("+15551234567", "https://example.com", True),
            ("5551234567", "https://example.com", True),
        ],
    )
    def test_country_specific_validation(self, phone, url, expected):
        """Тест валидации для разных стран"""

        assert PhoneValidator.is_likely_phone(phone, url) is expected

    def test_domain_country_mapping(self):
        """Тест маппинга доменов в коды стран"""

        from contact_parser.constants import DOMAIN_COUNTRY_MAP

        assert DOMAIN_COUNTRY_MAP.get("ru") == "7"
        assert DOMAIN_COUNTRY_MAP.get("by") == "375"
        assert DOMAIN_COUNTRY_MAP.get("ua") == "380"
        assert DOMAIN_COUNTRY_MAP.get("com") == "1"
        assert DOMAIN_COUNTRY_MAP.get("uk") == "44"
