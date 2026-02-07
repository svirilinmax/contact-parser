# src/contact_parser/__init__.py
"""
Contact Parser - Advanced website parser for extracting contact information

Основные классы:
    ContactParser - основной парсер
    ParserSettings - настройки парсера
    ContactInfo - модель результатов
"""

from .models import ContactInfo, ParserSettings
from .output import ResultSaver
from .parser import ContactParser
from .validators import EmailValidator, PhoneValidator

__version__ = "2.0.0"
__author__ = "Contact Parser Team"

__all__ = [
    "ContactParser",
    "ParserSettings",
    "ContactInfo",
    "PhoneValidator",
    "EmailValidator",
    "ResultSaver",
]
