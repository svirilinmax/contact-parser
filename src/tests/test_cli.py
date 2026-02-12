import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from contact_parser.cli import create_parser, load_settings, process_url, save_to_json_file
from contact_parser.models import ParserSettings


class TestCLI:
    """Тесты для командной строки"""

    def test_create_parser(self):
        """Тест создания парсера аргументов"""

        parser = create_parser()
        assert parser is not None
        # Проверяем описание и основные параметры
        assert "Парсер сайта" in parser.description
        assert "url" in parser.format_help().lower()
        assert "--output" in parser.format_help()

    def test_parser_help(self):
        """Тест вывода справки"""

        parser = create_parser()
        help_text = parser.format_help()
        assert "Парсер сайта" in help_text
        assert "--help" in help_text
        assert "Примеры использования" in help_text

    def test_parser_url_argument(self):
        """Тест парсинга URL аргумента"""

        parser = create_parser()
        args = parser.parse_args(["https://example.com"])
        assert args.url == "https://example.com"
        assert args.max_pages is None  # По умолчанию

    def test_parser_output_argument(self):
        """Тест парсинга --output аргумента"""

        parser = create_parser()
        args = parser.parse_args(["--output", "result.json", "https://example.com"])
        assert args.output == Path("result.json")
        assert args.url == "https://example.com"

    def test_parser_all_arguments(self):
        """Тест парсинга всех аргументов"""

        parser = create_parser()
        args = parser.parse_args(
            [
                "https://example.com",
                "--max-pages",
                "100",
                "--timeout",
                "30.0",
                "--delay",
                "1.0",
                "--workers",
                "10",
                "--output",
                "result.json",
                "--quiet",
                "--verbose",
                "--no-verify-ssl",
                "--simple-validation",
            ]
        )

        assert args.url == "https://example.com"
        assert args.max_pages == 100
        assert args.timeout == 30.0
        assert args.delay == 1.0
        assert args.workers == 10
        assert args.output == Path("result.json")
        assert args.quiet is True
        assert args.verbose is True
        assert args.no_verify_ssl is True
        assert args.simple_validation is True

    def test_load_settings_default(self):
        """Тест загрузки настроек по умолчанию"""

        args = MagicMock()
        args.config = None
        args.max_pages = None
        args.timeout = None
        args.delay = None
        args.workers = None
        args.no_verify_ssl = False
        args.simple_validation = False

        settings = load_settings(args)
        assert isinstance(settings, ParserSettings)
        assert settings.max_pages == 50
        assert settings.timeout == 15.0
        assert settings.request_delay == 0.2
        assert settings.max_workers == 5
        assert settings.verify_ssl is True

    def test_load_settings_from_args(self):
        """Тест загрузки настроек из аргументов"""

        args = MagicMock()
        args.config = None
        args.max_pages = 100
        args.timeout = 30.0
        args.delay = 1.0
        args.workers = 10
        args.no_verify_ssl = True
        args.simple_validation = True

        settings = load_settings(args)
        assert settings.max_pages == 100
        assert settings.timeout == 30.0
        assert settings.request_delay == 1.0
        assert settings.max_workers == 10
        assert settings.verify_ssl is False
        assert settings.enable_phone_validation is False
        assert settings.enable_email_validation is False

    @patch("contact_parser.cli.load_settings_from_file")
    @patch("pathlib.Path.exists")
    def test_load_settings_from_config_file(self, mock_exists, mock_load):
        """Тест загрузки настроек из файла конфигурации"""

        mock_settings = ParserSettings(max_pages=200, timeout=60.0)
        mock_load.return_value = mock_settings
        mock_exists.return_value = True

        args = MagicMock()
        args.config = Path("config.yaml")
        args.max_pages = None
        args.timeout = None
        args.delay = None
        args.workers = None
        args.no_verify_ssl = False
        args.simple_validation = False

        settings = load_settings(args)

        assert settings.max_pages == 200
        assert settings.timeout == 60.0
        mock_load.assert_called_once_with("config.yaml")

    @patch("pathlib.Path.exists")
    def test_load_settings_from_nonexistent_config_file(self, mock_exists):
        """Тест загрузки настроек из несуществующего файла"""

        mock_exists.return_value = False

        args = MagicMock()
        args.config = Path("nonexistent.yaml")

        with pytest.raises(SystemExit) as exc_info:
            load_settings(args)

        assert exc_info.value.code == 1

    def test_save_to_json_file(self, tmp_path):
        """Тест сохранения в JSON файл"""

        data = {"test": "data", "number": 123}
        filepath = tmp_path / "output.json"

        save_to_json_file(data, filepath, quiet=True)

        assert filepath.exists()
        with open(filepath, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            assert loaded == data

    def test_save_to_json_file_with_parent_dir(self, tmp_path):
        """Тест сохранения с созданием родительских директорий"""

        data = {"test": "data"}
        filepath = tmp_path / "deep" / "nested" / "output.json"

        assert not filepath.parent.exists()
        save_to_json_file(data, filepath, quiet=True)

        assert filepath.parent.exists()
        assert filepath.exists()

    @patch("contact_parser.cli.ContactParser")
    def test_process_url_success(self, MockParser):
        """Тест успешной обработки URL"""

        mock_contact_info = MagicMock()
        mock_contact_info.url = "https://example.com"
        mock_contact_info.emails = ["test@example.com"]
        mock_contact_info.phones = ["+79991234567"]

        mock_parser = MockParser.return_value
        mock_parser.parse_website.return_value = mock_contact_info

        settings = ParserSettings()
        result = process_url("https://example.com", settings)

        assert result["url"] == "https://example.com"
        assert result["emails"] == ["test@example.com"]
        assert result["phones"] == ["+79991234567"]
        MockParser.assert_called_once_with(settings)
        mock_parser.parse_website.assert_called_once_with("https://example.com")

    @patch("contact_parser.cli.ContactParser")
    @patch("contact_parser.cli.logger")
    def test_process_url_error(self, mock_logger, MockParser):
        """Тест обработки URL с ошибкой"""

        mock_parser = MockParser.return_value
        mock_parser.parse_website.side_effect = Exception("Test error")

        settings = ParserSettings()
        result = process_url("https://example.com", settings)

        assert result["url"] == "https://example.com"
        assert result["emails"] == []
        assert result["phones"] == []
        mock_logger.error.assert_called()
