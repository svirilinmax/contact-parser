import pytest

from contact_parser.extractors import DataExtractor
from contact_parser.models import ParserSettings
from contact_parser.validators import EmailValidator, PhoneValidator


class TestDataExtractor:
    """Тесты для DataExtractor"""

    @pytest.fixture
    def extractor(self):
        """Создает экземпляр DataExtractor для тестов"""

        settings = ParserSettings()
        return DataExtractor(settings)

    def test_extract_from_html_with_contacts(self, extractor):
        """Тест извлечения контактов из HTML"""

        html = """
        <html>
            <body>
                <p>Email: test@example.com</p>
                <p>Phone: +7 (999) 123-45-67</p>
                <a href="mailto:admin@example.com">Email us</a>
                <a href="tel:+79998765432">Call us</a>
                <a href="/about">About</a>
            </body>
        </html>
        """

        result = extractor.extract_from_html(html)

        # Email должны быть найдены
        assert len(result["emails"]) >= 1
        # Проверяем что хотя бы один из email присутствует
        found_emails = [e for e in result["emails"] if "test@example.com" in e or "admin@example.com" in e]
        assert len(found_emails) >= 1

        # Телефоны должны быть найдены и валидированы
        assert len(result["phones"]) >= 1

        # Ссылки должны быть найдены
        assert "/about" in result["links"]

    def test_extract_from_html_no_contacts(self, extractor):
        """Тест извлечения из HTML без контактов"""

        html = """
        <html>
            <body>
                <p>Some text without contacts</p>
                <a href="/page">Link</a>
            </body>
        </html>
        """

        result = extractor.extract_from_html(html)

        assert len(result["emails"]) == 0
        assert len(result["phones"]) == 0
        assert "/page" in result["links"]

    def test_extract_from_invalid_html(self, extractor):
        """Тест извлечения из невалидного HTML"""

        html = "<invalid>html</content>"

        result = extractor.extract_from_html(html)

        # Должен вернуть пустые структуры
        assert result["emails"] == set()
        assert result["phones"] == set()
        assert result["links"] == set()

    def test_extract_emails_from_mailto(self, extractor):
        """Тест извлечения email из mailto ссылок"""

        html = '<a href="mailto:realtest@gmail.com?subject=Hello">Email</a>'

        result = extractor.extract_from_html(html)

        # Проверяем что email найден (может быть нормализован)
        assert len(result["emails"]) >= 1
        assert any("realtest" in e and "gmail.com" in e for e in result["emails"])

    def test_extract_phones_from_tel(self, extractor):
        """Тест извлечения телефонов из tel ссылок"""
        html = '<a href="tel:+79991234567">Phone</a>'

        result = extractor.extract_from_html(html)

        assert len(result["phones"]) >= 1
        # Проверяем что номер содержит нужные цифры
        phone = list(result["phones"])[0]
        assert "79991234567" in phone or "9991234567" in phone


class TestPhoneValidator:
    """Тесты для PhoneValidator"""

    def test_is_likely_phone_valid(self):
        """Тест проверки валидных телефонов"""

        assert PhoneValidator.is_likely_phone("+79991234567") is True
        assert PhoneValidator.is_likely_phone("+375296167777") is True
        assert PhoneValidator.is_likely_phone("89991234567") is True
        assert PhoneValidator.is_likely_phone("+1 (555) 123-4567") is True

    def test_is_likely_phone_invalid(self):
        """Тест проверки невалидных телефонов"""

        assert PhoneValidator.is_likely_phone("123") is False
        assert PhoneValidator.is_likely_phone("") is False
        assert PhoneValidator.is_likely_phone("1726730819") is False  # ID товара
        assert PhoneValidator.is_likely_phone("00000000") is False  # Все нули
        assert PhoneValidator.is_likely_phone("12345678") is False  # Последовательность

    def test_normalize_phone_russian(self):
        """Тест нормализации российских телефонов"""

        result = PhoneValidator.normalize_phone("+7 (999) 123-45-67")
        assert result is not None
        assert "79991234567" in result

        result = PhoneValidator.normalize_phone("8(999)1234567")
        assert result is not None
        assert "79991234567" in result

    def test_normalize_phone_belarusian(self):
        """Тест нормализации белорусских телефонов"""

        result = PhoneValidator.normalize_phone("+375 29 616-77-77")
        assert result is not None
        assert "375" in result

    def test_normalize_phone_invalid(self):
        """Тест нормализации невалидных телефонов"""

        assert PhoneValidator.normalize_phone("") is None
        assert PhoneValidator.normalize_phone("123") is None
        assert PhoneValidator.normalize_phone("1726730819") is None


class TestEmailValidator:
    """Тесты для EmailValidator"""

    def test_is_valid_email_valid(self):
        """Тест проверки валидных email"""

        assert EmailValidator.is_valid_email("test@gmail.com") is True
        assert EmailValidator.is_valid_email("user.name@company.co.uk") is True
        assert EmailValidator.is_valid_email("admin123@site.org") is True

    def test_is_valid_email_invalid(self):
        """Тест проверки невалидных email"""

        assert EmailValidator.is_valid_email("test@com") is False
        assert EmailValidator.is_valid_email("test@.com") is False
        assert EmailValidator.is_valid_email("@example.com") is False
        assert EmailValidator.is_valid_email("test@example.com") is False  # Тестовый домен

    def test_normalize_email(self):
        """Тест нормализации email"""

        assert EmailValidator.normalize_email("  TEST@GMAIL.COM  ") == "test@gmail.com"
        assert EmailValidator.normalize_email("User@Site.ORG") == "user@site.org"

    def test_validate_and_normalize_emails(self):
        """Тест валидации и нормализации набора email"""

        emails = {
            "  TEST@GMAIL.COM  ",
            "admin@site.org",
            "invalid@com",  # Невалидный
            "test@example.com",  # Тестовый домен
        }

        result = EmailValidator.validate_and_normalize_emails(emails)

        assert "test@gmail.com" in result
        assert "admin@site.org" in result
        assert "invalid@com" not in result
        assert "test@example.com" not in result  # Должен быть отфильтрован
