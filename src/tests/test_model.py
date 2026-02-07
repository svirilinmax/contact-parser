import pytest
from pydantic import ValidationError

from contact_parser.models import ContactInfo, ParserSettings


class TestContactInfo:
    """Тесты для модели ContactInfo"""

    def test_valid_contact_info(self):
        """Тест создания валидного ContactInfo"""
        data = {
            "url": "https://example.com",
            "emails": ["test@gmail.com", "admin@yahoo.com"],  # Реальные домены
            "phones": ["+79991234567", "+375296167777"],
        }

        result = ContactInfo(**data)

        assert result.url == "https://example.com"
        assert "test@gmail.com" in result.emails
        assert "admin@yahoo.com" in result.emails
        assert "+79991234567" in result.phones

    def test_invalid_email(self):
        """Тест с невалидным email"""
        data = {
            "url": "https://example.com",
            "emails": ["notanemail", "bad@", "@bad.com"],
            "phones": [],
        }
        result = ContactInfo(**data)
        assert result.emails == []

    def test_invalid_phone(self):
        """Тест с невалидным телефоном"""
        data = {
            "url": "https://example.com",
            "emails": [],
            "phones": ["123", "abc", ""],  # Явно невалидные
        }
        result = ContactInfo(**data)
        assert result.phones == []

    def test_email_normalization(self):
        """Тест нормализации email"""
        data = {
            "url": "https://example.com",
            "emails": ["  TEST@GMAIL.COM  "],
            "phones": [],
        }
        result = ContactInfo(**data)
        if result.emails:
            assert result.emails[0] == "test@gmail.com"

        result = ContactInfo(**data)
        assert result.emails[0] == "test@example.com"  # Должен быть нижний регистр

    def test_empty_lists(self):
        """Тест с пустыми списками"""

        result = ContactInfo(url="https://example.com", emails=[], phones=[])

        assert result.emails == []
        assert result.phones == []

    def test_model_dump(self):
        """Тест сериализации модели"""

        data = {
            "url": "https://example.com",
            "emails": ["test@example.com"],
            "phones": ["+79991234567"],
        }

        model = ContactInfo(**data)
        dumped = model.model_dump()

        assert dumped["url"] == "https://example.com"
        assert dumped["emails"] == ["test@example.com"]
        assert dumped["phones"] == ["+79991234567"]


class TestParserSettings:
    """Тесты для модели ParserSettings"""

    def test_default_settings(self):
        """Тест настроек по умолчанию"""

        settings = ParserSettings()

        assert settings.max_pages == 50
        assert settings.timeout == 15.0
        assert settings.request_delay == 0.2
        assert settings.max_workers == 5
        assert settings.follow_redirects is True

    def test_custom_settings(self):
        """Тест кастомных настроек"""

        settings = ParserSettings(
            max_pages=100,
            timeout=30.0,
            request_delay=1.0,
            max_workers=10,
            follow_redirects=False,
        )

        assert settings.max_pages == 100
        assert settings.timeout == 30.0
        assert settings.request_delay == 1.0
        assert settings.max_workers == 10
        assert settings.follow_redirects is False

    def test_invalid_max_pages(self):
        """Тест невалидного значения max_pages"""

        with pytest.raises(ValidationError):
            ParserSettings(max_pages=0)  # Должно быть >= 1

    def test_invalid_timeout(self):
        """Тест невалидного значения timeout"""

        with pytest.raises(ValidationError):
            ParserSettings(timeout=0)  # Должно быть > 0

    def test_environment_variables(self):
        """Тест загрузки настроек из переменных окружения"""

        import os

        # Устанавливаем переменные окружения
        os.environ["CONTACT_PARSER_MAX_PAGES"] = "100"
        os.environ["CONTACT_PARSER_TIMEOUT"] = "20.0"

        # Создаем настройки
        settings = ParserSettings()

        # Проверяем, что значения загрузились из переменных окружения
        assert settings.max_pages == 100
        assert settings.timeout == 20.0

        # Очищаем переменные окружения
        del os.environ["CONTACT_PARSER_MAX_PAGES"]
        del os.environ["CONTACT_PARSER_TIMEOUT"]

    def test_email_pattern(self):
        """Тест паттерна для email"""

        settings = ParserSettings()

        # Проверяем, что паттерн является строкой
        assert isinstance(settings.email_pattern, str)
        assert len(settings.email_pattern) > 0

    def test_phone_patterns(self):
        """Тест паттернов для телефонов"""

        settings = ParserSettings()

        # Проверяем, что это список строк
        assert isinstance(settings.phone_patterns, list)
        assert len(settings.phone_patterns) > 0
        assert all(isinstance(pattern, str) for pattern in settings.phone_patterns)
