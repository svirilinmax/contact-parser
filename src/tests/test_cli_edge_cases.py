import logging
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

            from contact_parser.cli import process_url

            process_url("https://example.com", MagicMock())

            assert mock_logger.debug.called
            mock_logger.isEnabledFor.assert_called_with(logging.DEBUG)

    def test_cli_verbose_mode_logging(self):
        """Тест verbose режима с выводом настроек"""
        with patch("sys.argv", ["contact-parser", "https://example.com", "--verbose"]):
            with patch("contact_parser.cli.logger") as mock_logger:
                with patch("contact_parser.cli.ContactParser") as MockParser:
                    mock_parser = MockParser.return_value
                    mock_contact_info = MagicMock()
                    mock_contact_info.url = "https://example.com"
                    mock_contact_info.emails = []
                    mock_contact_info.phones = []
                    mock_parser.parse_website.return_value = mock_contact_info

                    main()
                    mock_logger.debug.assert_called()

    def test_cli_simple_validation(self):
        """Тест --simple-validation флага"""
        with patch("sys.argv", ["contact-parser", "https://example.com", "--simple-validation"]):
            with patch("contact_parser.cli.load_settings") as mock_load:
                main()
                args = mock_load.call_args[0][0]
                assert args.simple_validation is True

    def test_cli_output_permission_error(self, tmp_path):
        """Тест ошибки прав доступа при сохранении"""

        from contact_parser.cli import save_to_json_file

        file_path = tmp_path / "test_output.json"
        data_to_save = {"emails": ["test@test.com"], "phones": []}

        with patch("contact_parser.cli.open", side_effect=PermissionError("Доступ запрещен")):
            with pytest.raises(PermissionError):
                save_to_json_file(data_to_save, file_path)
