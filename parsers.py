from typing import Any, Generic, List, Optional, Tuple, Type, TypeVar, get_type_hints

T1 = TypeVar("T1")
T2 = TypeVar("T2")


class BaseParser(Generic[T1, T2]):

    origin_type: T1
    return_type: T2

    def __init__(self) -> None:
        super().__init__()

    def get_parse_types(self) -> List[Tuple[Type[T1], Type[Optional[T2]]]]:
        hints = get_type_hints(self)
        origin_type = hints["origin_type"]
        return_type = hints["return_type"]

        return [
            (origin_type, Optional[return_type]),
            (Optional[origin_type], Optional[return_type]),
            (origin_type, return_type),
        ]

    def __call__(self, value: Optional[T1]) -> Optional[T2]:

        if value is None:
            return None

        return self.parse(value)

    def parse(self, value: T1) -> T2:
        raise NotImplementedError


class IntStrParser(BaseParser[int, str]):

    origin_type: int
    return_type: str

    def parse(self, value: int) -> str:
        return str(value)


class StrIntParser(BaseParser[str, int]):

    origin_type: str
    return_type: int

    def parse(self, value: str) -> int:
        return int(value)


class DjangoRelatedField:
    def all(self) -> Any:
        ...

    def order_by(self, *args, **kwargs) -> Any:
        ...
