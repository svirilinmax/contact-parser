import argparse
import json
import logging
import sys
from pathlib import Path

from .config import load_settings_from_file, setup_logging
from .models import ParserSettings
from .parser import ContactParser

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки"""

    parser = argparse.ArgumentParser(
        description="Парсер сайта для извлечения контактной информации",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s https://example.com
  %(prog)s https://example.com --max-pages 100 --output results.json
  %(prog)s https://example.com --config config.yaml --verbose
  %(prog)s https://example.com --quiet --output contacts.json
        """,
    )

    parser.add_argument("url", nargs="?", help="URL сайта для парсинга")

    parser.add_argument("--config", type=Path, help="Путь к файлу конфигурации")

    # Основные настройки парсера
    parser.add_argument("--max-pages", type=int, help="Максимальное количество страниц для обхода")

    parser.add_argument("--timeout", type=float, help="Таймаут для HTTP-запросов в секундах")

    parser.add_argument("--delay", type=float, help="Задержка между запросами в секундах")

    parser.add_argument("--workers", type=int, help="Количество потоков для параллельной обработки")

    # Настройки вывода
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Путь к файлу для сохранения результатов (JSON)",
    )

    # Режимы работы
    parser.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Тихий режим (только JSON в stdout, ошибки в stderr)",
    )

    # Логирование
    parser.add_argument("--log-file", type=Path, help="Путь к файлу для записи логов")

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Уровень детализации логов (только в stderr)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Включить подробный вывод (эквивалентно --log-level=DEBUG)",
    )

    # Безопасность
    parser.add_argument(
        "--no-verify-ssl",
        action="store_true",
        help="Отключить проверку SSL сертификатов",
    )

    # Пакетная обработка
    parser.add_argument("--batch", type=Path, help="Файл со списком URL для пакетной обработки")

    # TODO: Добавить опцию для отключения улучшенной валидации
    parser.add_argument(
        "--simple-validation",
        action="store_true",
        help="Использовать простую валидацию (быстрее, но менее точно)",
    )

    return parser


def load_settings(args: argparse.Namespace) -> ParserSettings:
    """Загружает настройки из различных источников"""

    settings_kwargs = {}

    # Загружаем из файла конфигурации, если указан
    if args.config:
        if not args.config.exists():
            print(f"Ошибка: Файл конфигурации не найден: {args.config}", file=sys.stderr)
            sys.exit(1)

        try:
            return load_settings_from_file(str(args.config))
        except Exception as e:
            print(f"Ошибка загрузки конфигурации: {e}", file=sys.stderr)
            sys.exit(1)

    # Загружаем настройки из аргументов командной строки
    if args.max_pages is not None:
        settings_kwargs["max_pages"] = args.max_pages

    if args.timeout is not None:
        settings_kwargs["timeout"] = args.timeout

    if args.delay is not None:
        settings_kwargs["request_delay"] = args.delay

    if args.workers is not None:
        settings_kwargs["max_workers"] = args.workers

    if args.no_verify_ssl:
        settings_kwargs["verify_ssl"] = False

    # TODO: Настройка валидации из аргументов CLI
    if args.simple_validation:
        settings_kwargs["enable_phone_validation"] = False
        settings_kwargs["enable_email_validation"] = False

    # Создаем настройки
    try:
        return ParserSettings(**settings_kwargs)
    except Exception as e:
        print(f"Ошибка создания настроек: {e}", file=sys.stderr)
        sys.exit(1)


def save_to_json_file(data: dict, filepath: Path, quiet: bool = False):
    """Сохраняет данные в JSON файл"""
    try:
        # Создаем директорию если её нет
        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        if not quiet:
            print(f"✓ Результаты сохранены в {filepath}", file=sys.stderr)
    except Exception as e:
        print(f"Ошибка сохранения файла: {e}", file=sys.stderr)
        raise


def process_url(url: str, settings: ParserSettings) -> dict:
    """Обрабатывает один URL - ТОЧНО ПО ТЗ"""
    try:
        # Создаем парсер
        parser = ContactParser(settings)

        # Парсим сайт
        contact_info = parser.parse_website(url)

        result = {
            "url": str(contact_info.url),
            "emails": contact_info.emails,
            "phones": contact_info.phones,
        }

        # TODO: Добавить дополнительную информацию для отладки
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"Обработан URL {url}: "
                f"найдено {len(result['emails'])} email, "
                f"{len(result['phones'])} телефонов"
            )

        return result

    except Exception as e:
        logger.error(f"Ошибка при обработке {url}: {e}")
        return {"url": url, "emails": [], "phones": []}


def main() -> None:
    """Основная функция CLI"""
    parser = create_parser()
    args = parser.parse_args()

    # Проверяем обязательные аргументы
    if not args.url and not args.batch:
        parser.print_help()
        print("\nОшибка: Не указан URL для парсинга", file=sys.stderr)
        sys.exit(1)

    # Настраиваем логирование (все логи только в stderr!)
    log_level = "DEBUG" if args.verbose else args.log_level

    # В тихом режиме логи только ERROR и выше
    if args.quiet:
        log_level = "ERROR"
        # TODO: В тихом режиме также скрываем прогресс-бары
        logging.getLogger("urllib3").setLevel(logging.CRITICAL)
        logging.getLogger("requests").setLevel(logging.CRITICAL)

    setup_logging(level=log_level, log_file=args.log_file)

    try:
        # Загружаем настройки
        settings = load_settings(args)

        # TODO: Вывести информацию о настройках (только в verbose режиме)
        if args.verbose:
            logger.debug(
                f"Используемые настройки: "
                f"max_pages={settings.max_pages}, "
                f"timeout={settings.timeout}, "
                f"workers={settings.max_workers}, "
                f"phone_validation={'вкл' if settings.enable_phone_validation else 'выкл'}"
            )

        # Пакетная обработка
        if args.batch:
            if not args.batch.exists():
                print(f"Ошибка: Файл не найден: {args.batch}", file=sys.stderr)
                sys.exit(1)

            urls = args.batch.read_text(encoding="utf-8").strip().splitlines()
            urls = [url.strip() for url in urls if url.strip()]

            if not urls:
                print("Ошибка: Файл не содержит валидных URL", file=sys.stderr)
                sys.exit(1)

            all_results = []
            for i, url in enumerate(urls):
                # TODO: Выводить прогресс для пакетной обработки
                if not args.quiet:
                    print(f"Обработка {i + 1}/{len(urls)}: {url}", file=sys.stderr)

                result = process_url(url, settings)
                all_results.append(result)

            # Сохраняем все результаты
            if args.output:
                save_to_json_file(all_results, args.output, args.quiet)
            else:
                print(json.dumps(all_results, ensure_ascii=False, indent=2))

        # Обработка одного URL
        else:
            # Парсим сайт
            result = process_url(args.url, settings)

            # Сохраняем результаты
            if args.output:
                save_to_json_file(result, args.output, args.quiet)
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))

    except KeyboardInterrupt:
        logger.info("Парсер остановлен пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"Критическая ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
