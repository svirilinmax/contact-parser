# Contact Parser

### Парсер сайтов для извлечения контактной информации (email и телефоны) на Python.

## Возможности

- **Извлечение контактов** - email и телефоны со всего сайта
- **Обход сайта** - в пределах одного домена
- **Валидация email** - проверка формата и доменов
- **Валидация телефонов** - поддержка международных форматов
- **Многопоточность** - параллельная обработка страниц
- **Конфигурируемость** - настройки через CLI, файлы, env переменные
- **Экспорт результатов** - JSON формат с метаданными

## Установка

### Из исходного кода:

```bash
    git clone https://github.com/ваш-репозиторий/contact-parser.git
    cd contact-parser
    pip install -e .
```

### Из PyPI (после публикации):

```bash
    pip install contact-parser
```

## Использование

### Базовое использование:

```bash
    contact-parser https://example.com
```

### С сохранением в файл:

```bash
    contact-parser https://example.com --output results.json
```

### С дополнительными настройками:

```bash
    contact-parser https://example.com \
      --max-pages 100 \
      --timeout 30 \
      --workers 10 \
      --output contacts.json \
      --verbose
```

### Пакетная обработка:

```bash
    contact-parser --batch urls.txt --output-dir ./results
```

## Формат результатов

```json
{
  "url": "https://example.com",
  "emails": ["contact@example.com", "support@example.com"],
  "phones": ["+79991234567", "+375296167777"],
  "_metadata": {
    "generated_at": "2024-01-15T10:30:00",
    "parser_version": "2.0.0"
  }
}
```

## Конфигурация

### Через аргументы командной строки:

| Аргумент | Описание | По умолчанию |
|----------|----------|--------------|
| `--max-pages` | Максимум страниц для обхода | 50 |
| `--timeout` | Таймаут запросов (сек) | 15 |
| `--delay` | Задержка между запросами (сек) | 0.2 |
| `--workers` | Количество потоков | 5 |
| `--output` | Файл для сохранения результатов | stdout |
| `--config` | Файл конфигурации | - |
| `--quiet` | Тихий режим | false |

### Через переменные окружения:

```bash
    export CONTACT_PARSER_MAX_PAGES=100
    export CONTACT_PARSER_TIMEOUT=30.0
    export CONTACT_PARSER_REQUEST_DELAY=1.0
```

### Через файл конфигурации:

Создайте `config.py`:

```python
    max_pages = 100
    timeout = 30.0
    request_delay = 1.0
    max_workers = 10
    enable_phone_validation = True
    enable_email_validation = True
```

Использование:

```bash
    contact-parser https://example.com --config config.py
```

## Требования

- Python 3.8+
- requests>=2.32.0
- lxml>=6.0.0
- pydantic>=2.12.0
- phonenumbers>=8.13.0

## Разработка

### Установка для разработки:

```bash
    git clone https://github.com/svirilinmax/contact-parser.git
    cd contact-parser
    pip install -e ".[dev]"
    pre-commit install
```

### Запуск тестов:

```bash
    pytest --cov=src/contact_parser --cov-report=term-missing
```

### Проверка кода:

```bash
    black src/
    isort src/
    flake8 src/
```

## Архитектура

```
contact-parser/
├── src/
│   └── contact_parser/
│       ├── __init__.py           # Основной модуль
│       ├── cli.py               # Интерфейс командной строки
│       ├── parser.py            # Основной класс парсера
│       ├── crawler.py           # Обход сайта
│       ├── extractors.py        # Извлечение данных
│       ├── models.py            # Модели данных
│       ├── validators.py        # Валидация email и телефонов
│       ├── output.py            # Сохранение результатов
│       ├── utils.py             # Вспомогательные функции
│       ├── config.py            # Настройка логирования
│       ├── exceptions.py        # Исключения
│       └── __main__.py          # Точка входа для python -m
├── src/tests/                   # Тесты
├── pyproject.toml              # Конфигурация проекта
├── requirements.txt            # Зависимости
├── .pre-commit-config.yaml     # Pre-commit хуки
└── run_example.py              # Пример использования
```

## Ограничения

- Обход только в пределах одного домена
- Не поддерживает JavaScript-рендеринг
- Максимальный размер страницы: 10MB
- Максимальное количество страниц: 1000 (настраивается)

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функциональности
3. Добавьте тесты
4. Запустите pytest и pre-commit
5. Создайте Pull Request

## Лицензия

MIT
