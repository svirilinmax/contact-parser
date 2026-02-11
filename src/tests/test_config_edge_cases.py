import logging

from contact_parser.config import load_settings_from_file, setup_logging


class TestConfigEdgeCases:
    """Тесты для крайних случаев конфигурации"""

    def test_setup_logging_invalid_level(self):
        """Тест настройки логирования с невалидным уровнем"""

        setup_logging(level="INVALID_LEVEL")
        assert logging.getLogger().level == logging.INFO

    def test_setup_logging_file_error(self, capsys):
        """Тест ошибки при создании файла лога"""

        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            invalid_path = tmp_dir

            setup_logging(log_file=invalid_path)

            captured = capsys.readouterr()

            assert "Ошибка файлового логирования" in captured.err
            assert len(logging.getLogger().handlers) > 0

    def test_load_settings_from_file_with_comments(self, tmp_path):
        """Тест загрузки из файла с комментариями"""

        config_file = tmp_path / "config.py"
        config_file.write_text(
            """
# Это комментарий
max_pages = 150  # Комментарий в строке
timeout = 45.0
# Ещё комментарий
"""
        )

        settings = load_settings_from_file(str(config_file))
        assert settings.max_pages == 150
        assert settings.timeout == 45.0

    def test_load_settings_from_file_with_imports(self, tmp_path):
        """Тест загрузки из файла с импортами"""

        config_file = tmp_path / "config.py"
        config_file.write_text(
            """
import os
from datetime import datetime

max_pages = int(os.getenv('TEST_MAX_PAGES', '100'))
timestamp = datetime.now()
"""
        )

        settings = load_settings_from_file(str(config_file))
        assert settings.max_pages == 100
