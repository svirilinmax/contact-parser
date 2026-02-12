from contact_parser.utils import HTMLParser, PatternMatcher, URLNormalizer


class TestURLNormalizerAdvanced:
    """Расширенные тесты для URLNormalizer"""

    def test_normalize_url_edge_cases(self):
        """Тест нормализации крайних случаев"""

        # Пустые и некорректные URL
        assert URLNormalizer.normalize_url("", "https://example.com") is None
        assert URLNormalizer.normalize_url("#anchor", "https://example.com") is None
        assert URLNormalizer.normalize_url("mailto:test@example.com", "https://example.com") is None
        assert URLNormalizer.normalize_url("javascript:void(0)", "https://example.com") is None

        # Относительные URL
        result = URLNormalizer.normalize_url("/about", "https://example.com")
        assert result == "https://example.com/about"

        # URL с параметрами
        result = URLNormalizer.normalize_url("/page?param=value", "https://example.com")
        assert result == "https://example.com/page"

        # URL с якорем
        result = URLNormalizer.normalize_url("/page#section", "https://example.com")
        assert result == "https://example.com/page"

    def test_is_same_domain_edge_cases(self):
        """Тест проверки домена (крайние случаи)"""

        assert URLNormalizer.is_same_domain("https://example.com", "example.com") is True
        assert URLNormalizer.is_same_domain("https://sub.example.com", "example.com") is True
        assert URLNormalizer.is_same_domain("https://example.org", "example.com") is False
        assert URLNormalizer.is_same_domain("", "example.com") is False
        assert URLNormalizer.is_same_domain("/relative", "example.com") is True  # Относительный URL

        # Некорректные URL
        assert URLNormalizer.is_same_domain("not-a-url", "example.com") is False

    def test_validate_url_edge_cases(self):
        """Тест валидации URL (крайние случаи)"""

        assert URLNormalizer.validate_url("https://example.com") is True
        assert URLNormalizer.validate_url("http://example.com") is True
        assert URLNormalizer.validate_url("ftp://example.com") is True
        assert URLNormalizer.validate_url("example.com") is False
        assert URLNormalizer.validate_url("") is False
        assert URLNormalizer.validate_url("://") is False

        # URL с портом
        assert URLNormalizer.validate_url("https://example.com:8080") is True

    def test_get_domain_edge_cases(self):
        """Тест извлечения домена"""

        assert URLNormalizer.get_domain("https://example.com") == "example.com"
        assert URLNormalizer.get_domain("https://sub.example.com:8080/path") == "sub.example.com:8080"
        assert URLNormalizer.get_domain("") is None
        assert URLNormalizer.get_domain("not-a-url") is None


class TestHTMLParserAdvanced:
    """Расширенные тесты для HTMLParser"""

    def test_extract_text_edge_cases(self):
        """Тест извлечения текста (крайние случаи)"""

        html = """
        <html>
            <head><script>alert('test');</script><style>body { color: red; }</style></head>
            <body>Visible text</body>
        </html>
        """
        tree = HTMLParser.parse_html(html)
        text = HTMLParser.extract_text(tree)

        assert "Visible text" in text

        # Пустое дерево
        text = HTMLParser.extract_text(None)
        assert text == ""

    def test_extract_links_edge_cases(self):
        """Тест извлечения ссылок (крайние случаи)"""

        html = """
        <html>
            <body>
                <a href="/relative">Relative</a>
                <a href="https://external.com">External</a>
                <a>No href</a>
                <a href="">Empty href</a>
                <a href="  spaced  ">Spaced</a>
            </body>
        </html>
        """
        tree = HTMLParser.parse_html(html)
        links = HTMLParser.extract_links(tree, "https://example.com")

        assert "/relative" in links
        assert "https://external.com" in links
        assert "" in links or " " in str(links)
        assert len(links) >= 3

    def test_parse_html_edge_cases(self):
        """Тест парсинга HTML (крайние случаи)"""

        # Пустой HTML
        tree = HTMLParser.parse_html("")
        assert tree is None

        # HTML с невалидными символами
        tree = HTMLParser.parse_html("<html>\x00</html>")
        assert tree is not None

        # Очень большой HTML
        large_html = "<html>" + "x" * 10000 + "</html>"
        tree = HTMLParser.parse_html(large_html)
        assert tree is not None

    def test_clean_html_edge_cases(self):
        """Тест очистки HTML (крайние случаи)"""

        # HTML с комментариями
        html = "<!-- Comment --><html><body>Text</body></html>"
        cleaned = HTMLParser.clean_html(html)
        assert "Text" in cleaned

        # Невалидный HTML
        html = "<div>Unclosed"
        cleaned = HTMLParser.clean_html(html)
        assert isinstance(cleaned, str)

        # Пустой HTML
        cleaned = HTMLParser.clean_html("")
        assert cleaned == ""


class TestPatternMatcherAdvanced:
    """Расширенные тесты для PatternMatcher"""

    def test_compile_patterns_edge_cases(self):
        """Тест компиляции паттернов (крайние случаи)"""

        # Пустой список паттернов
        patterns = PatternMatcher.compile_patterns([])
        assert patterns == []

        # Паттерны с ошибками
        patterns = PatternMatcher.compile_patterns(["(invalid", r"\d+"])
        # Должен скомпилировать только валидные
        assert len(patterns) == 1

        # Паттерны с флагами в строке
        patterns = PatternMatcher.compile_patterns([r"(?i)test", r"(?m)multiline"])
        assert len(patterns) == 2

    def test_find_all_matches_edge_cases(self):
        """Тест поиска совпадений (крайние случаи)"""

        # Пустой текст
        patterns = PatternMatcher.compile_patterns([r"\d+"])
        matches = PatternMatcher.find_all_matches("", patterns)
        assert matches == set()

        # Пустой список паттернов
        matches = PatternMatcher.find_all_matches("text", [])
        assert matches == set()

        # Текст без совпадений
        patterns = PatternMatcher.compile_patterns([r"\d+"])
        matches = PatternMatcher.find_all_matches("no digits here", patterns)
        assert matches == set()

        # Множественные совпадения
        patterns = PatternMatcher.compile_patterns([r"\d+", r"[a-z]+"])
        matches = PatternMatcher.find_all_matches("123 abc 456", patterns)
        assert "123" in matches
        assert "abc" in matches
        assert "456" in matches

    def test_url_normalizer_get_domain_edge(self):
        """Тест извлечения домена из URL с граничными случаями"""

        assert URLNormalizer.get_domain("") is None
        assert URLNormalizer.get_domain("   ") is None
        assert URLNormalizer.get_domain("example.com") == "example.com"
        assert URLNormalizer.get_domain("http://") is None

    def test_html_parser_clean_html_error(self):
        """Тест ошибки при очистке HTML"""

        parser = HTMLParser()
        result = parser.clean_html("<invalid>html")
        assert "<invalid>html" in result

    def test_pattern_matcher_compile_error(self):
        """Тест ошибки компиляции паттерна"""

        matcher = PatternMatcher()
        patterns = matcher.compile_patterns([r"[invalid", r"\d{3}-\d{2}"])
        assert len(patterns) == 1  # Только валидный
