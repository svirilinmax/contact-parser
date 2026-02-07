import logging
import sys
from pathlib import Path
from typing import Optional

from .models import ParserSettings

# Инициализируем логгер для этого модуля
logger = logging.getLogger(__name__)


def setup_logging(
    level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """
    Настраивает логирование для приложения

    Важно: В stdout НИЧЕГО не выводится, только в stderr или файл
    """

    log_level = getattr(logging, level.upper()) if level else logging.INFO

    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Создаем форматтер
    formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")

    # Создаем обработчик для stderr (НЕ stdout!)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(log_level)

    # Настраиваем корневой логгер
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Удаляем существующие обработчики
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Добавляем обработчик stderr
    root_logger.addHandler(stderr_handler)

    # Добавляем файловый обработчик, если указан
    if log_file:
        try:
            # Создаем директорию для логов, если её нет
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            root_logger.addHandler(file_handler)

            # Сообщение о файле логирования тоже в stderr
            logger.info(f"Логи будут записываться в файл: {log_file}")
        except Exception as e:
            logger.error(f"Не удалось настроить файловое логирование: {e}")

    # Устанавливаем уровень для сторонних библиотек
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("lxml").setLevel(logging.WARNING)


def load_settings_from_env() -> ParserSettings:
    """
    Загружает настройки из переменных окружения

    Returns:
        ParserSettings: Настройки парсера
    """
    try:
        settings = ParserSettings()
        logger.info("Настройки загружены из переменных окружения")
        return settings
    except Exception as e:
        logger.error(f"Ошибка загрузки настроек из переменных окружения: {e}")
        raise


def load_settings_from_file(config_file: str) -> ParserSettings:
    """
    Загружает настройки из файла конфигурации

    Args:
        config_file: Путь к файлу конфигурации

    Returns:
        ParserSettings: Настройки парсера
    """
    try:
        from importlib.machinery import SourceFileLoader

        # Загружаем модуль из файла
        loader = SourceFileLoader("config_module", config_file)
        module = loader.load_module()

        # Ищем настройки в модуле
        settings_dict = {}
        for key in ParserSettings.model_fields.keys():
            if hasattr(module, key):
                settings_dict[key] = getattr(module, key)

        if not settings_dict:
            raise ValueError(f"Не найдено настроек в файле {config_file}")

        settings = ParserSettings(**settings_dict)
        logger.info(f"Настройки загружены из файла: {config_file}")
        return settings

    except Exception as e:
        logger.error(f"Ошибка загрузки настроек из файла {config_file}: {e}")
        raise
