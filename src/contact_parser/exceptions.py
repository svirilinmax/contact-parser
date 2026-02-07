class ParserError(Exception):
    """Базовое исключение для парсера"""

    pass


class InvalidURLError(ParserError):
    """Некорректный URL"""

    pass


class NetworkError(ParserError):
    """Ошибка сети"""

    pass


class MaxPagesLimitError(ParserError):
    """Достигнут лимит страниц"""

    pass


class ContentTypeError(ParserError):
    """Неподдерживаемый тип контента"""

    pass
