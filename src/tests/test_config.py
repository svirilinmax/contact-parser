"""Тесты для модуля конфигурации"""
import logging
import os

import pytest

from contact_parser.config import load_settings_from_env, load_settings_from_file, setup_logging


class TestConfig:
    """Тесты для модуля конфигурации"""

    def test_setup_logging_default(self, capsys):
        """Тест настройки логирования по умолчанию"""

        # Сначала сбросим все обработчики
        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        setup_logging(level="INFO")

        logger = logging.getLogger(__name__)
        logger.info("Test message")

        # Принудительно сбрасываем буферы
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "flush"):
                handler.flush()

        captured = capsys.readouterr()
        assert "Test message" in captured.err

    def test_setup_logging_debug(self, capsys):
        """Тест настройки логирования с уровнем DEBUG"""

        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        setup_logging(level="DEBUG")

        logger = logging.getLogger(__name__)
        logger.debug("Debug message")

        captured = capsys.readouterr()
        assert "Debug message" in captured.err

    def test_setup_logging_with_file(self, tmp_path):
        """Тест настройки логирования с файлом"""

        log_file = tmp_path / "test.log"

        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        setup_logging(level="INFO", log_file=str(log_file))

        logger = logging.getLogger(__name__)
        logger.info("File test message")

        # Принудительно сбрасываем буферы
        for handler in logging.getLogger().handlers:
            handler.flush()
            if hasattr(handler, "close"):
                handler.close()

        assert log_file.exists()
        log_content = log_file.read_text(encoding="utf-8")
        assert "File test message" in log_content

    def test_setup_logging_silence_third_party(self):
        """Тест отключения логирования сторонних библиотек"""

        for handler in logging.getLogger().handlers[:]:
            logging.getLogger().removeHandler(handler)

        setup_logging(level="INFO")

        assert logging.getLogger("urllib3").level == logging.WARNING
        assert logging.getLogger("requests").level == logging.WARNING
        assert logging.getLogger("lxml").level == logging.WARNING

    def test_load_settings_from_env(self, monkeypatch):
        """Тест загрузки настроек из переменных окружения"""

        # Сохраняем старые значения
        old_max_pages = os.environ.get("CONTACT_PARSER_MAX_PAGES")
        old_timeout = os.environ.get("CONTACT_PARSER_TIMEOUT")

        try:
            monkeypatch.setenv("CONTACT_PARSER_MAX_PAGES", "100")
            monkeypatch.setenv("CONTACT_PARSER_TIMEOUT", "30.0")
            monkeypatch.setenv("CONTACT_PARSER_REQUEST_DELAY", "1.0")

            settings = load_settings_from_env()

            assert settings.max_pages == 100
            assert settings.timeout == 30.0
            assert settings.request_delay == 1.0
        finally:
            # Восстанавливаем старые значения
            if old_max_pages is not None:
                monkeypatch.setenv("CONTACT_PARSER_MAX_PAGES", old_max_pages)
            else:
                monkeypatch.delenv("CONTACT_PARSER_MAX_PAGES", raising=False)

            if old_timeout is not None:
                monkeypatch.setenv("CONTACT_PARSER_TIMEOUT", old_timeout)
            else:
                monkeypatch.delenv("CONTACT_PARSER_TIMEOUT", raising=False)

    def test_load_settings_from_file_python(self, tmp_path):
        """Тест загрузки настроек из Python файла"""

        config_file = tmp_path / "config.py"
        # Без лишних отступов!
        config_file.write_text(
            """max_pages = 200
timeout = 60.0
request_delay = 2.0
max_workers = 8
verify_ssl = False
enable_phone_validation = True
enable_email_validation = True"""
        )

        settings = load_settings_from_file(str(config_file))

        assert settings.max_pages == 200
        assert settings.timeout == 60.0
        assert settings.request_delay == 2.0
        assert settings.max_workers == 8
        assert settings.verify_ssl is False
        assert settings.enable_phone_validation is True
        assert settings.enable_email_validation is True

    def test_load_settings_from_file_empty(self, tmp_path):
        """Тест загрузки настроек из пустого файла"""

        config_file = tmp_path / "empty_config.py"
        config_file.write_text("")

        with pytest.raises(ValueError) as exc_info:
            load_settings_from_file(str(config_file))

        # Проверяем что сообщение содержит нужные слова
        error_message = str(exc_info.value)
        assert "пуст" in error_message or "не найдено" in error_message.lower()

    def test_load_settings_from_file_nonexistent(self):
        """Тест загрузки настроек из несуществующего файла"""

        with pytest.raises(FileNotFoundError) as exc_info:
            load_settings_from_file("/nonexistent/config.py")

        # Проверяем что сообщение содержит нужные слова
        error_message = str(exc_info.value)
        assert "не найден" in error_message.lower() or "no such file" in error_message.lower()

    def test_load_settings_from_file_partial(self, tmp_path):
        """Тест загрузки настроек из файла с частичными настройками"""

        config_file = tmp_path / "partial_config.py"
        # Без лишних отступов!
        config_file.write_text(
            """max_pages = 150
timeout = 45.0"""
        )

        settings = load_settings_from_file(str(config_file))

        assert settings.max_pages == 150
        assert settings.timeout == 45.0
        # Проверяем значения по умолчанию для других настроек
        assert settings.request_delay == 0.2
        assert settings.max_workers == 5

    def test_load_settings_from_file_invalid_content(self, tmp_path):
        """Тест загрузки настроек из файла с невалидным содержимым"""

        config_file = tmp_path / "invalid_config.py"
        # Без лишних отступов!
        config_file.write_text(
            """max_pages = "не число"
timeout = "не float\""""
        )

        with pytest.raises(Exception) as exc_info:
            load_settings_from_file(str(config_file))

        # Проверяем что это какая-то ошибка
        assert exc_info.value is not None

    def test_load_settings_from_file_with_syntax_error(self, tmp_path):
        """Тест загрузки настроек из файла с синтаксической ошибкой"""

        config_file = tmp_path / "syntax_error.py"
        config_file.write_text(
            """max_pages = 100
timeout = invalid syntax"""
        )

        with pytest.raises(ValueError) as exc_info:
            load_settings_from_file(str(config_file))

        error_message = str(exc_info.value)
        assert "синтаксическая ошибка" in error_message.lower() or "syntax" in error_message.lower()
