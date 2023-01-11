from typing import Any, Callable, Dict, Generic, Iterable, List, Optional, Tuple, Type, TypeVar, get_type_hints

from converter.exceptions import ConfigError, ParsingError

from .parsers import BaseParser, DjangoRelatedField, IntStrParser, StrIntParser

OriginClass = TypeVar("OriginClass", bound=Any)
ReturnClass = TypeVar("ReturnClass", bound=Any)


ComputeItem = Tuple[str, Callable[[OriginClass], Any]]
RenameItem = Tuple[str, str]
ReturnTypeHintItem = Tuple[str, Any]


class BaseConverter(Generic[OriginClass, ReturnClass]):
    """Базовый конвертер.


    Конфигурация:
        origin_class: Класс из которого конвертируем
        return_class: Класс в который конвертируем
        return_compute_fields: Список атрибутов для return_class, которые вычисляются динамически.
        Формат элемента: (имя в return_class, метод).

        rename_pairs: Кастомный маппинг атрибутов между origin_class и return_class.
        Если нужно смапить разноименные атрибуты, используйте маппинг.
        Формат элемента: (имя в origin_class, имя в return_class)

        return_type_hints: Список дополнительных анотации типов для атрибутов return_class.
        Формат элемента: (имя в return_class, тип)

        exclude_fields: Список атрибутов return_class, которые не должны участвовать в конвертации,
        для них значение не будет передано в конструктор.
        Формат элемента: (имя в return_class)

    """

    origin_class: OriginClass
    return_class: ReturnClass

    return_compute_fields: List[ComputeItem] = []
    rename_pairs: List[RenameItem] = []

    return_type_hints: List[ReturnTypeHintItem] = []

    exclude_fields: List[str] = []

    def __init__(self) -> None:
        self._setup_convert_classes()
        self._setup_parsers()
        self._setup_attrs()

    def _setup_convert_classes(self) -> None:
        """Подготовить классы для конвертации."""
        hints = get_type_hints(type(self))
        self._return_class = hints["return_class"]
        self._origin_class = hints["origin_class"]

    def _setup_parsers(self) -> None:
        """Подготовить парсеры для конвертации."""
        self._parsers_mapping = {}
        for parser in self._get_parsers():
            parse_types = {type_: parser for type_ in parser.get_parse_types()}
            self._parsers_mapping.update(parse_types)

    def _setup_attrs(self) -> None:
        """Подготовить списки атрибутов для разных этапов конвертации

        Raises:
            ConfigError: ошибка в параметрах парсера.
        """
        # вычисляемые атрибуты
        self._compute_fields_mapping = dict(self.return_compute_fields)
        return_compute_attrs_set = set(self._compute_fields_mapping.keys())

        # атрибуты из исходного класса
        self.origin_attrs = self._get_origin_attrs()

        # атрибуты класса, в который конвертируем
        self.return_hints = get_type_hints(self._return_class)
        self.return_hints.update(dict(self.return_type_hints))
        if len(self.return_hints) == 0:
            raise ConfigError(
                "Для return_class не заданы type_hints, настройте их в return_class,"
                "или передайте через return_type_hints"
            )
        self.return_attrs = set(self.return_hints.keys()) - set(self.exclude_fields) - return_compute_attrs_set

        # атрибуты, которые маппятся на разные имена
        self.origin_rename, self.return_rename = self._parse_rename_mapping(self.rename_pairs)
        return_rename_set = set(self.return_rename)
        if len(return_rename_set) != len(self.return_rename):
            raise ConfigError(
                f"return_rename_fields: атрибуты, предназначенные для return_class должны быть уникальными,"
                f"найдены дубликаты: {self.return_rename}"
            )

        # атрибуты, которые маппятся на одно и то же имя
        self.origin_contains = (self.return_attrs - return_rename_set).intersection(self.origin_attrs)

    def convert(self, instance: OriginClass) -> ReturnClass:
        """Перевести экземпляр класса в формат return_class

        Args:
            instance: экземпляр

        Returns:
            ReturnClass: экземпляр класса return_class
        Raises:
            ParsingError: ошибка в парсинге.
            ComputeError: ошибка в при вызове метода.
        """
        contains_result = self._parse_samename(self.origin_contains, instance)
        rename_result = self._parse_rename(self.origin_rename, self.return_rename, instance)
        need_compute_result = self._parse_need_compute(instance)

        ReturnClass = self.get_return_class()
        return ReturnClass(**contains_result, **rename_result, **need_compute_result)

    def get_return_class(self) -> Type[ReturnClass]:
        return self._return_class

    def _parse_rename_mapping(self, doublet: List[RenameItem]) -> Tuple[List[str], List[str]]:
        origin_rename = []
        return_rename = []
        for item in doublet:
            origin_rename.append(item[0])
            return_rename.append(item[1])
        return origin_rename, return_rename

    def _parse_samename(self, origin: Iterable[str], instance: OriginClass) -> Dict[str, Any]:
        return self._parse_rename(origin, origin, instance)

    def _parse_rename(self, origin: Iterable[str], return_: Iterable[str], instance: OriginClass) -> Dict[str, Any]:
        result = {}
        for attr_from, attr_to in zip(origin, return_):
            val = getattr(instance, attr_from)
            val_type = self._get_origin_value_type(val)
            return_type = self.return_hints[attr_to]
            if val_type != return_type and Optional[val_type] != return_type and not isinstance(val, type(None)):
                try:
                    val = self._parsers_mapping[val_type, return_type](val)
                except (KeyError, ValueError) as e:
                    raise ParsingError(attr_from, attr_to) from e
            result[attr_to] = val
        return result

    def _parse_need_compute(self, instance: OriginClass) -> Dict[str, Any]:
        result = {}
        for attr, func in self._compute_fields_mapping.items():
            result[attr] = func(instance)
        return result

    def _get_parsers(self) -> List[BaseParser]:
        """Набор парсеров для конвертации.

        Returns:
            List[BaseParser]: парсеры
        """
        return [
            StrIntParser(),
            IntStrParser(),
        ]

    def _get_origin_value_type(self, val: Any) -> Type[Any]:
        """Определить тип значения из origin_class

        Args:
            val (Any): значение

        Returns:
            Type[Any]: тип
        """
        return type(val)

    def _get_origin_attrs(self) -> List[str]:
        """Получить список атрибутов origin_class.

        В списке должны быть атрибуты, значения которых могут быть переданы в return_class

        Returns:
            List[str]: список атрибутов origin_class
        """
        return list(get_type_hints(self._origin_class).keys())


class DjangoConverter(BaseConverter[OriginClass, ReturnClass]):
    """Конвертер с поддержкой моделей джанги."""

    def _get_origin_attrs(self) -> List[str]:
        return list(self._origin_class._meta._forward_fields_map.keys())

    def _get_origin_value_type(self, val: Any) -> Type[Any]:
        if hasattr(val, "all"):
            # TODO улучшить распозновалку для джанги
            return DjangoRelatedField
        return type(val)


# TODO Улучшить анализатор, добавить поддержку дефолтов в датаклассах
# Чтобы понимать нужен атрибут или нет, и не приходилось заносить его в exclude
