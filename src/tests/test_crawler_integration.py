from unittest.mock import Mock, patch

import pytest

from contact_parser.crawler import WebsiteCrawler
from contact_parser.models import ParserSettings


class TestWebsiteCrawlerIntegration:
    """Интеграционные тесты для WebsiteCrawler"""

    @pytest.fixture
    def crawler(self):
        """Создает экземпляр WebsiteCrawler для тестов"""
        settings = ParserSettings(max_pages=5, timeout=5.0, request_delay=0, max_workers=1)
        return WebsiteCrawler(settings)

    @patch("requests.Session.get")
    def test_crawl_single_page(self, mock_get, crawler):
        """Тест обхода одной страницы"""
        html_content = """
        <html>
            <body>
                <p>Email: test@gmail.com</p>
                <a href="https://example.com/about">About</a>
            </body>
        </html>
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}
        mock_response.url = "https://example.com"
        mock_response.text = html_content
        mock_response.content = html_content.encode("utf-8")  # Исправлено: не пустые байты
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = crawler.crawl("https://example.com", max_pages=1)

        assert len(result) == 1
        assert "test@gmail.com" in result[0]["emails"]

    @patch("requests.Session.get")
    def test_crawl_multiple_pages(self, mock_get, crawler):
        """Тест обхода нескольких страниц"""

        def get_side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html; charset=utf-8"}
            mock_response.url = url
            mock_response.raise_for_status = Mock()

            if url.rstrip("/") == "https://example.com":
                html = """
                <html>
                    <body>
                        <a href="https://example.com/page1">Page 1</a>
                        <a href="https://example.com/page2">Page 2</a>
                    </body>
                </html>
                """
            elif "page1" in url:
                html = "<html><body><p>Email: page1@gmail.com</p></body></html>"
            elif "page2" in url:
                html = "<html><body>Phone: 8-916-123-45-67</body></html>"
            else:
                html = "<html><body></body></html>"

            mock_response.text = html
            mock_response.content = html.encode("utf-8")
            return mock_response

        mock_get.side_effect = get_side_effect
        crawler.settings.enable_phone_validation = False

        result = crawler.crawl("https://example.com", max_pages=3)

        assert len(result) == 3

        all_emails = set()
        all_phones = set()
        for page in result:
            all_emails.update(page["emails"])
            all_phones.update(page["phones"])

        assert "page1@gmail.com" in all_emails

        # Более гибкая проверка телефонов
        phone_found = False
        for phone in all_phones:
            if "9161234567" in phone.replace("-", "").replace(" ", ""):
                phone_found = True
                break

        assert phone_found, f"Phone not found. List: {all_phones}"

    @patch("requests.Session.get")
    def test_crawl_with_network_error(self, mock_get, crawler):
        """Тест обхода с ошибками сети"""
        mock_get.side_effect = Exception("Network error")
        result = crawler.crawl("https://example.com", max_pages=1)
        assert len(result) == 0
