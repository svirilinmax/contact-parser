from contact_parser.utils import HTMLParser


class TestHTMLParser:
    """Тесты для парсера HTML с использованием lxml"""

    def test_parse_valid_html(self):
        """Тест парсинга валидного HTML"""

        html = "<html><body><h1>Hello World</h1></body></html>"
        tree = HTMLParser.parse_html(html)

        assert tree is not None
        assert tree.tag == "html"

    def test_parse_invalid_html(self):
        """Тест парсинга невалидного HTML"""

        html = "<invalid><tag>"
        tree = HTMLParser.parse_html(html)

        # lxml может парсить даже невалидный HTML
        assert tree is not None

    def test_extract_text(self):
        """Тест извлечения текста из HTML"""

        html = """
        <html>
            <body>
                <h1>Title</h1>
                <p>Paragraph with <b>bold</b> text.</p>
            </body>
        </html>
        """

        tree = HTMLParser.parse_html(html)
        text = HTMLParser.extract_text(tree)

        assert "Title" in text
        assert "Paragraph with bold text." in text

    def test_extract_links(self):
        """Тест извлечения ссылок из HTML"""

        html = """
        <html>
            <body>
                <a href="/page1">Page 1</a>
                <a href="https://example.com/page2">Page 2</a>
                <a href="#anchor">Anchor</a>
                <a href="mailto:test@example.com">Email</a>
            </body>
        </html>
        """

        tree = HTMLParser.parse_html(html)
        links = HTMLParser.extract_links(tree, "https://example.com")

        assert "/page1" in links
        assert "https://example.com/page2" in links
        assert "#anchor" in links
        assert "mailto:test@example.com" in links
        assert len(links) == 4

    def test_clean_html(self):
        """Тест очистки HTML"""
        html = """
        <html>
            <head>
                <script>alert('test');</script>
                <style>body { color: red; }</style>
            </head>
            <body>
                <h1>Content</h1>
                <noscript>JS disabled</noscript>
            </body>
        </html>
        """

        cleaned = HTMLParser.clean_html(html)

        assert isinstance(cleaned, str)
        assert len(cleaned) > 0
        assert "Content" in cleaned or "content" in cleaned.lower()

    def test_extract_text_empty(self):
        """Тест извлечения текста из пустого дерева"""

        text = HTMLParser.extract_text(None)
        assert text == ""

    def test_extract_links_empty(self):
        """Тест извлечения ссылок из пустого дерева"""

        links = HTMLParser.extract_links(None, "https://example.com")
        assert links == set()
