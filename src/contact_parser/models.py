from typing import List

from pydantic import BaseModel, Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ContactInfo(BaseModel):
    url: HttpUrl
    emails: List[str] = Field(default_factory=list, description="Найденные email адреса")
    phones: List[str] = Field(default_factory=list, description="Найденные телефонные номера")

    @field_validator("emails")
    def validate_emails_list(cls, emails: List[str]) -> List[str]:
        """Более мягкая валидация email"""
        results = []
        for email in emails:
            # Простая проверка на наличие @
            if "@" in email and "." in email.split("@")[1]:
                results.append(email.lower().strip())
        return results

    @field_validator("phones")
    def validate_phones_list(cls, phones: List[str]) -> List[str]:
        """Более мягкая валидация телефонов"""
        results = []
        for phone in phones:
            # Простая проверка: содержит цифры и имеет разумную длину
            digits = "".join(filter(str.isdigit, phone))
            if 6 <= len(digits) <= 15:
                results.append(phone.strip())
        return results


class ParserSettings(BaseSettings):
    """Настройки парсера с валидацией через Pydantic"""

    # Основные настройки
    max_pages: int = Field(
        default=50,
        ge=1,
        le=1000,
        description="Максимальное количество страниц для обхода",
    )

    timeout: float = Field(default=15.0, gt=0, le=60.0, description="Таймаут для HTTP-запросов в секундах")

    request_delay: float = Field(default=0.2, ge=0, le=5.0, description="Задержка между запросами в секундах")

    max_workers: int = Field(default=5, ge=1, le=20, description="Максимальное количество потоков")

    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User-Agent для HTTP-запросов",
    )

    # Дополнительные настройки для парсинга
    follow_redirects: bool = Field(default=True, description="Следовать перенаправлениям")
    verify_ssl: bool = Field(default=True, description="Проверять SSL сертификаты")

    # НАСТРОЙКИ ВАЛИДАЦИИ (ДОБАВЛЯЕМ НОВЫЕ)
    enable_phone_validation: bool = Field(default=True, description="Включить улучшенную валидацию телефонов")

    enable_email_validation: bool = Field(default=True, description="Включить улучшенную валидацию email")

    min_phone_length: int = Field(default=10, ge=5, le=15, description="Минимальная длина телефонного номера")

    max_phone_length: int = Field(default=15, ge=10, le=20, description="Максимальная длина телефонного номера")

    # Настройки для извлечения данных
    email_pattern: str = Field(
        default=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        description="Регулярное выражение для поиска email",
    )

    phone_patterns: List[str] = Field(
        default_factory=lambda: [
            # Универсальные паттерны
            r"\+\d{1,4}[-\s]?\(?\d{1,5}\)?[-\s]?\d{1,5}[-\s]?\d{1,5}[-\s]?\d{1,5}",
            # Российские номера
            r"\+7[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            r"8[-\s]?\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Формы без кода страны
            r"\(?\d{3,4}\)?[-\s]?\d{2,3}[-\s]?\d{2,3}[-\s]?\d{2,4}",
            # Короткие форматы
            r"\d{3}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
            # Белорусские номера
            r"\+375[-\s]?\d{2}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}",
        ],
        description="Регулярные выражения для поиска телефонов",
    )

    model_config = SettingsConfigDict(env_prefix="CONTACT_PARSER_", case_sensitive=False)
