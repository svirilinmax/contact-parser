from unittest.mock import patch

import pytest

from contact_parser.models import ParserSettings
from contact_parser.parser import ContactParser


class TestContactParserIntegration:
    """Интеграционные тесты для ContactParser"""

    @pytest.fixture
    def parser(self):
        """Создает экземпляр ContactParser для тестов"""

        settings = ParserSettings(max_pages=3, timeout=5.0, request_delay=0, max_workers=1)
        return ContactParser(settings)

    @patch("contact_parser.crawler.WebsiteCrawler.crawl")
    def test_parse_website_success(self, mock_crawl, parser):
        """Тест успешного парсинга сайта"""

        mock_crawl.return_value = [
            {
                "url": "https://example.com",
                "emails": {"test@example.com"},
                "phones": {"+79991234567"},
                "links": set(),
            },
            {
                "url": "https://example.com/about",
                "emails": {"admin@example.com"},
                "phones": set(),
                "links": set(),
            },
        ]

        result = parser.parse_website("https://example.com")

        assert result.url == "https://example.com"
        assert len(result.emails) == 2
        assert len(result.phones) == 1
        assert "test@example.com" in result.emails
        assert "admin@example.com" in result.emails
        assert any("79991234567" in p for p in result.phones)

    @patch("contact_parser.crawler.WebsiteCrawler.crawl")
    def test_parse_website_empty(self, mock_crawl, parser):
        """Тест парсинга сайта без контактов"""

        mock_crawl.return_value = [
            {
                "url": "https://example.com",
                "emails": set(),
                "phones": set(),
                "links": set(),
            }
        ]

        result = parser.parse_website("https://example.com")

        assert result.url == "https://example.com"
        assert len(result.emails) == 0
        assert len(result.phones) == 0

    def test_parse_website_invalid_url(self, parser):
        """Тест парсинга с невалидным URL"""

        result = parser.parse_website("invalid-url")
        assert result.emails == []
        assert result.phones == []

    def test_parse_website_empty_string(self, parser):
        """Тест парсинга с пустой строкой"""

        result = parser.parse_website("")

        assert result.emails == []
        assert result.phones == []

    @patch("contact_parser.crawler.WebsiteCrawler.crawl")
    def test_parse_website_error_handling(self, mock_crawl, parser):
        """Тест обработки ошибок при парсинге"""

        mock_crawl.side_effect = Exception("Test error")

        result = parser.parse_website("https://example.com")
        assert result.emails == []
        assert result.phones == []
