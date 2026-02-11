from unittest.mock import MagicMock, patch

import pytest

from contact_parser.cli import main


class TestCLIIntegration:
    """Интеграционные тесты CLI с реальными вызовами"""

    @patch("contact_parser.cli.argparse.ArgumentParser.parse_args")
    @patch("contact_parser.cli.setup_logging")
    @patch("contact_parser.cli.ContactParser")
    def test_main_success(self, MockParser, mock_setup_logging, mock_parse_args):
        """Тест успешного запуска main"""

        # Мокаем аргументы
        mock_args = MagicMock()
        mock_args.url = "https://example.com"
        mock_args.config = None
        mock_args.max_pages = None
        mock_args.timeout = None
        mock_args.delay = None
        mock_args.workers = None
        mock_args.output = None
        mock_args.quiet = False
        mock_args.verbose = False
        mock_args.no_verify_ssl = False
        mock_args.simple_validation = False
        mock_args.batch = None
        mock_args.log_file = None
        mock_args.log_level = "INFO"
        mock_parse_args.return_value = mock_args

        # Мокаем парсер
        mock_parser = MockParser.return_value
        mock_contact_info = MagicMock()
        mock_contact_info.url = "https://example.com"
        mock_contact_info.emails = ["test@example.com"]
        mock_contact_info.phones = ["+79991234567"]
        mock_parser.parse_website.return_value = mock_contact_info

        # Запускаем main
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write = MagicMock()
            main()

        # Проверяем что всё было вызвано
        mock_setup_logging.assert_called_once()
        MockParser.assert_called_once()
        mock_parser.parse_website.assert_called_once_with("https://example.com")

    @patch("sys.argv", ["contact-parser", "https://example.com", "--max-pages", "10"])
    @patch("contact_parser.cli.setup_logging")
    @patch("contact_parser.cli.ContactParser")
    def test_main_with_args(self, MockParser, mock_setup_logging):
        """Тест запуска с аргументами"""

        # Мокаем парсер
        mock_parser = MockParser.return_value
        mock_contact_info = MagicMock()
        mock_contact_info.url = "https://example.com"
        mock_contact_info.emails = []
        mock_contact_info.phones = []
        mock_parser.parse_website.return_value = mock_contact_info

        # Запускаем main
        with patch("sys.stdout") as mock_stdout:
            mock_stdout.write = MagicMock()
            main()

        mock_setup_logging.assert_called_once()

    def test_main_without_url(self):
        """Тест запуска без URL"""

        with patch("sys.argv", ["contact-parser"]):
            with patch("sys.exit") as mock_exit:
                main()
                mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["contact-parser", "--help"])
    def test_main_help(self, capsys):
        """Тест вывода справки"""

        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with pytest.raises(SystemExit):
                main()

            captured = capsys.readouterr()

            assert "Парсер сайта" in captured.out
            mock_exit.assert_called_once_with(0)

    @patch("sys.argv", ["contact-parser", "--config", "nonexistent.yaml", "https://example.com"])
    def test_main_config_file_not_found(self):
        """Тест с несуществующим файлом конфигурации"""

        with patch("sys.exit", side_effect=SystemExit) as mock_exit:
            with patch("pathlib.Path.exists", return_value=False):
                try:
                    main()
                except SystemExit:
                    pass

                mock_exit.assert_called_once_with(1)

    @patch("sys.argv", ["contact-parser", "--batch", "urls.txt", "--output", "results.json"])
    @patch("contact_parser.cli.setup_logging")
    @patch("contact_parser.cli.ContactParser")
    @patch("pathlib.Path.exists", return_value=True)
    def test_main_batch_mode(self, mock_exists, MockParser, mock_setup_logging, tmp_path):
        """Тест пакетного режима"""

        # Создаем временный файл с URL
        batch_file = tmp_path / "urls.txt"
        batch_file.write_text("https://example1.com\nhttps://example2.com\n")

        # Мокаем аргументы через sys.argv
        with patch("sys.argv", ["contact-parser", "--batch", str(batch_file), "--output", "results.json"]):
            # Мокаем парсер
            mock_parser = MockParser.return_value
            mock_contact_info = MagicMock()
            mock_contact_info.url = "https://example.com"
            mock_contact_info.emails = []
            mock_contact_info.phones = []
            mock_parser.parse_website.return_value = mock_contact_info

            # Мокаем save_to_json_file
            with patch("contact_parser.cli.save_to_json_file") as mock_save:
                with patch("sys.stdout") as mock_stdout:
                    mock_stdout.write = MagicMock()
                    main()

                # Проверяем что save был вызван
                mock_save.assert_called_once()
