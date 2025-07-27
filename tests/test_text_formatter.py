import unittest
from unittest.mock import patch
from src.utils.text_formatter import escape_markdown_v2, sanitize_markdown, format_bold, format_italic, format_list

class TestTextFormatter(unittest.TestCase):

    def test_escape_markdown_v2(self):
        self.assertEqual(escape_markdown_v2("_*[]()~`>#+-=|{}.!"), "\\_\\*\\[\\]\\(\\)\\~\\`\\>\\#\\+\\-\\=\\|\\{\\}\\.\\!")

    def test_sanitize_markdown(self):
        self.assertEqual(sanitize_markdown("Hello\r\nWorld"), "Hello\nWorld")
        self.assertEqual(sanitize_markdown("Hello\x00World"), "HelloWorld")

    def test_format_bold(self):
        self.assertEqual(format_bold("Hello World"), "*Hello World*")

    def test_format_italic(self):
        self.assertEqual(format_italic("Hello World"), "_Hello World_")

    def test_format_list(self):
        self.assertEqual(format_list(["one", "two", "three"]), "1\\. one\n2\\. two\n3\\. three")

if __name__ == '__main__':
    unittest.main()
