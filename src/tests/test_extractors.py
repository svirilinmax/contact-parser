import pytest

from contact_parser.extractors import DataExtractor
from contact_parser.models import ParserSettings
from contact_parser.validators import EmailValidator, PhoneValidator


class TestPhoneValidator:
    """Тесты для PhoneValidator"""

    def test_is_likely_phone_valid(self):
        """Тест проверки валидных телефонов с контекстом домена"""

        # Российские номера
        assert PhoneValidator.is_likely_phone("+79991234567", "https://example.ru") is True
        assert PhoneValidator.is_likely_phone("89991234567", "https://example.ru") is True
        assert PhoneValidator.is_likely_phone("89161234567", "https://example.ru") is True

        # Белорусские номера
        assert PhoneValidator.is_likely_phone("+375296167777", "https://example.by") is True
        assert PhoneValidator.is_likely_phone("375296167777", "https://example.by") is True
        assert PhoneValidator.is_likely_phone("291234567", "https://example.by") is True

        # Украинские номера
        assert PhoneValidator.is_likely_phone("+380501234567", "https://example.ua") is True
        assert PhoneValidator.is_likely_phone("501234567", "https://example.ua") is True

        # Американские номера
        assert PhoneValidator.is_likely_phone("+15551234567", "https://example.com") is True
        assert PhoneValidator.is_likely_phone("5551234567", "https://example.com") is True

    def test_is_likely_phone_invalid(self):
        """Тест проверки невалидных телефонов"""

        # Слишком короткие
        assert PhoneValidator.is_likely_phone("123") is False
        assert PhoneValidator.is_likely_phone("") is False

        # ID товаров
        assert PhoneValidator.is_likely_phone("1726730819", "https://example.ru") is False
        assert PhoneValidator.is_likely_phone("4941234567", "https://example.ru") is False

        # Невалидные коды стран
        assert PhoneValidator.is_likely_phone("+71589871646", "https://example.ru") is False
        assert PhoneValidator.is_likely_phone("+71127760297", "https://example.ru") is False

        # Последовательности
        assert PhoneValidator.is_likely_phone("12345678", "https://example.ru") is False
        assert PhoneValidator.is_likely_phone("00000000", "https://example.ru") is False

    def test_normalize_phone_russian(self):
        """Тест нормализации российских телефонов"""

        # С контекстом домена
        result = PhoneValidator.normalize_phone("+7 (999) 123-45-67", "https://example.ru")
        assert result == "+79991234567"

        result = PhoneValidator.normalize_phone("8(999)1234567", "https://example.ru")
        assert result == "+79991234567"

        result = PhoneValidator.normalize_phone("9991234567", "https://example.ru")
        assert result == "+79991234567"

        # Без контекста - не должно нормализоваться
        result = PhoneValidator.normalize_phone("9991234567")
        assert result is None

    def test_normalize_phone_belarusian(self):
        """Тест нормализации белорусских телефонов"""

        result = PhoneValidator.normalize_phone("+375 29 616-77-77", "https://example.by")
        assert result == "+375296167777"

        result = PhoneValidator.normalize_phone("291234567", "https://example.by")
        assert result == "+375291234567"

        result = PhoneValidator.normalize_phone("375291234567", "https://example.by")
        assert result == "+375291234567"

    def test_normalize_phone_edge_cases(self):
        """Тест нормализации телефонов (крайние случаи)"""

        # Украинские номера
        assert PhoneValidator.normalize_phone("+380501234567", "https://example.ua") == "+380501234567"
        assert PhoneValidator.normalize_phone("501234567", "https://example.ua") == "+380501234567"

        # Казахстанские
        assert PhoneValidator.normalize_phone("+77011234567", "https://example.kz") == "+77011234567"

        # Некорректные длины
        assert PhoneValidator.normalize_phone("123456789", "https://example.ru") is None
        assert PhoneValidator.normalize_phone("1234567890123456", "https://example.ru") is None

        # Специальные номера
        assert PhoneValidator.normalize_phone("88001234567", "https://example.ru") == "+78001234567"

    def test_validate_and_normalize_phones(self):
        """Тест валидации и нормализации набора телефонов"""

        url = "https://example.ru"
        phones = {
            "+7 (999) 123-45-67",
            "8(916)1234567",
            "invalid",
            "123",
            "4941234567",
            "+375296167777",
            "9161234567",
        }

        result = PhoneValidator.validate_and_normalize_phones(phones, url)

        assert len(result) == 2
        assert all(p.startswith("+7") for p in result)


class TestPhoneValidatorAdvanced:
    """Тесты для PhoneValidator"""

    def test_clean_phone(self):
        """Тест очистки телефонного номера"""

        assert PhoneValidator._clean_phone("+7 (999) 123-45-67") == "+79991234567"
        assert PhoneValidator._clean_phone("8-916-123-45-67") == "89161234567"
        assert PhoneValidator._clean_phone("+1 (555) 123-4567") == "+15551234567"
        assert PhoneValidator._clean_phone("") == ""
        assert PhoneValidator._clean_phone("abc") == ""
        assert PhoneValidator._clean_phone("+1+2+3") == "+123"

    def test_is_sequential(self):
        """Тест проверки последовательных цифр"""

        assert PhoneValidator._is_sequential("123456") is True
        assert PhoneValidator._is_sequential("234567") is True
        assert PhoneValidator._is_sequential("987654") is True
        assert PhoneValidator._is_sequential("123") is False
        assert PhoneValidator._is_sequential("111111") is False

    def test_is_too_perfect(self):
        """Тест проверки 'идеальных' паттернов"""

        assert PhoneValidator._is_too_perfect("12121212") is True
        assert PhoneValidator._is_too_perfect("123321") is True
        assert PhoneValidator._is_too_perfect("111111") is True
        assert PhoneValidator._is_too_perfect("9161234567") is False

    def test_is_valid_length_for_country(self):
        """Тест проверки длины по стандарту страны"""

        # Россия
        assert PhoneValidator._is_valid_length_for_country("79991234567", "7", has_plus=True) is True
        assert PhoneValidator._is_valid_length_for_country("9161234567", "7", has_plus=False) is True
        assert PhoneValidator._is_valid_length_for_country("999123456", "7", has_plus=False) is False  # 9 цифр

        # Беларусь
        assert PhoneValidator._is_valid_length_for_country("375291234567", "375", has_plus=True) is True
        assert PhoneValidator._is_valid_length_for_country("291234567", "375", has_plus=False) is True
        assert PhoneValidator._is_valid_length_for_country("37599999999", "375", has_plus=True) is False  # 11 цифр


class TestEmailValidatorAdvanced:
    """Тесты для EmailValidator"""

    def test_is_valid_email_edge_cases(self):
        """Тест валидации email (крайние случаи)"""

        # Валидные
        assert EmailValidator.is_valid_email("test+filter@gmail.com") is True
        assert EmailValidator.is_valid_email("user_name@real-domain.com") is True
        assert EmailValidator.is_valid_email("first.last@real-domain.co.uk") is True
        assert EmailValidator.is_valid_email("test@123.com") is True
        assert EmailValidator.is_valid_email("test@example.technology") is True

        # Невалидные
        assert EmailValidator.is_valid_email("test@com") is False
        assert EmailValidator.is_valid_email("test@.com") is False
        assert EmailValidator.is_valid_email("@example.com") is False
        assert EmailValidator.is_valid_email("test!@domain.com") is False
        assert EmailValidator.is_valid_email("test@domain!.com") is False

        # Длина
        long_local = "a" * 65
        assert EmailValidator.is_valid_email(f"{long_local}@gmail.com") is False


class TestDataExtractorAdvanced:
    """Тесты для DataExtractor"""

    @pytest.fixture
    def extractor_universal(self):
        """Создает экземпляр DataExtractor с отключенной валидацией"""

        settings = ParserSettings(enable_phone_validation=False)
        return DataExtractor(settings)

    def test_extract_phones_universal(self, extractor_universal):
        """Тест универсального извлечения телефонов"""

        html = """
        <html>
            <body>
                <p>US: +1-555-123-4567</p>
                <p>UK: +44 20 7946 0958</p>
                <p>RU: 8 (999) 123-45-67</p>
                <p>BY: +375 29 616-77-77</p>
            </body>
        </html>
        """

        result = extractor_universal.extract_from_html(html)
        assert len(result["phones"]) >= 4

    def test_extract_from_html_with_scripts(self):
        """Тест извлечения данных из HTML со скриптами"""

        html = """
        <html>
            <body>
                <script>
                    var phone = "+7 (999) 123-45-67";
                    var email = "hidden@gmail.com";
                </script>
                <div style="display:none">
                    Phone: 8-916-123-45-67
                </div>
            </body>
        </html>
        """

        extractor = DataExtractor(ParserSettings(enable_phone_validation=False))
        result = extractor.extract_from_html(html)

        # Должны найти данные в скриптах и скрытых элементах
        assert len(result["emails"]) >= 1
        assert len(result["phones"]) >= 2
