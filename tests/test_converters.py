from dataclasses import dataclass

import pytest

from converter.converters import BaseConverter
from converter.exceptions import ConfigError, ParsingError


@dataclass
class A:
    attr1: int
    attr2: str


@dataclass
class B:
    attr1: int
    attr2: int


@dataclass
class C:
    attr1: int
    attr2: int
    attr3: int


@dataclass
class D:
    attr1: bytes


class ABConverter(BaseConverter[A, B]):
    origin_class: A
    return_class: B


class ACRenameConverter(BaseConverter[A, C]):
    origin_class: A
    return_class: C
    rename_pairs = (("attr1", "attr3"),)


class ACComputeConverter(BaseConverter[A, C]):
    origin_class: A
    return_class: C
    return_compute_fields = (("attr3", lambda x: x.attr1),)


class ADConverter(BaseConverter[A, D]):
    origin_class: A
    return_class: D


class EmptyTypeHints(BaseConverter[A, object]):
    origin_class: A
    return_class: object


class DoubleRename(BaseConverter[A, B]):
    origin_class: A
    return_class: B

    rename_pairs = [
        ("attr1", "attr2"),
        ("attr1", "attr2"),
    ]


class TestBaseConverter:
    def test_convert(self):
        a = A(1, "1")
        cn = ABConverter()

        b = cn.convert(a)

        assert isinstance(b.attr1, int)
        assert isinstance(b.attr2, int)

    def test_convert_with_rename(self):
        a = A(1, "1")
        c = ACRenameConverter().convert(a)

        assert isinstance(c.attr1, int)
        assert isinstance(c.attr2, int)
        assert isinstance(c.attr3, int)

    def test_convert_with_compute(self):
        a = A(1, "1")
        c = ACComputeConverter().convert(a)

        assert isinstance(c.attr1, int)
        assert isinstance(c.attr2, int)
        assert isinstance(c.attr3, int)

    def test_parse_error(self):
        a = A(1, "1")
        with pytest.raises(ParsingError):
            ADConverter().convert(a)

    def test_congig_error_empty_type_hints(self):
        with pytest.raises(ConfigError):
            EmptyTypeHints()

    def test_congig_error_double_in_rename(self):
        with pytest.raises(ConfigError):
            DoubleRename()
