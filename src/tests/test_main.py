import sys
from unittest.mock import patch


def test_main_module():
    """Тест запуска модуля через python -m"""

    with patch.object(sys, "argv", ["contact_parser"]):
        with patch("contact_parser.cli.main") as mock_main:
            from contact_parser import __main__

            __main__.main()
            assert mock_main.called
