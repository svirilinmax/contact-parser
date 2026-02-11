from unittest.mock import MagicMock, patch

import pytest

from contact_parser.cli import load_settings, main


class TestCLIEdgeCases:
    """Тесты для крайних случаев CLI"""

    @patch("sys.argv", ["contact-parser"])
    def test_main_no_args(self):
        """Тест запуска без аргументов"""

        with patch("sys.exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["contact-parser", "https://example.com", "--config", "config.yaml"])
    @patch("pathlib.Path.exists", return_value=False)
    def test_main_config_not_found(self, mock_exists):
        """Тест с несуществующим файлом конфигурации"""

        with patch("sys.exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["contact-parser", "--batch", "empty.txt"])
    @patch("pathlib.Path.exists", return_value=True)
    @patch("pathlib.Path.read_text", return_value="")
    def test_main_batch_empty_file(self, mock_read, mock_exists):
        """Тест с пустым файлом для пакетной обработки"""

        with patch("sys.exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["contact-parser", "https://example.com", "--quiet"])
    @patch("contact_parser.cli.setup_logging")
    @patch("contact_parser.cli.ContactParser")
    def test_main_quiet_mode(self, MockParser, mock_setup_logging):
        """Тест тихого режима"""

        mock_parser = MockParser.return_value
        mock_contact_info = MagicMock()
        mock_contact_info.url = "https://example.com"
        mock_contact_info.emails = []
        mock_contact_info.phones = []
        mock_parser.parse_website.return_value = mock_contact_info

        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write = MagicMock()
            main()

        mock_setup_logging.assert_called_once()
        args, kwargs = mock_setup_logging.call_args
        assert kwargs.get("level") == "ERROR"

    def test_load_settings_invalid_args(self):
        """Тест загрузки настроек с невалидными аргументами"""

        args = MagicMock()
        args.config = None
        args.max_pages = -1
        args.timeout = -10.0
        args.delay = -0.5
        args.workers = 0
        args.no_verify_ssl = False
        args.simple_validation = False

        with pytest.raises(SystemExit):
            load_settings(args)

    @patch("contact_parser.cli.ContactParser")
    def test_process_url_debug_logging(self, MockParser):
        """Тест обработки URL с debug логированием"""

        mock_contact_info = MagicMock()
        mock_contact_info.url = "https://example.com"
        mock_contact_info.emails = []
        mock_contact_info.phones = []

        mock_parser = MockParser.return_value
        mock_parser.parse_website.return_value = mock_contact_info

        with patch("contact_parser.cli.logger") as mock_logger:
            mock_logger.isEnabledFor.return_value = True

            mock_logger.debug.assert_called_once()
