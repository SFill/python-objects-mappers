from converter.parsers import BaseParser, IntStrParser, StrIntParser


class TestParsers:
    def test_strint_parser(self):
        assert StrIntParser()("1") == 1

    def test_intstr_parser(self):
        assert IntStrParser()(1) == "1"

    def test_none_base_parser(self):
        assert BaseParser()(None) is None
