class BaseException(Exception):
    """Базовая ошибка конвертации."""


class ParsingError(BaseException):
    """Ошибка парсинга атрибута."""

    def __init__(self, attr_from: str, attr_to: str) -> None:
        super().__init__(f"Ошибка при конвертации атрибутов {attr_from} и {attr_to}")
        self.attr_from = attr_from
        self.attr_to = attr_to


class ConfigError(BaseException):
    """Ошибка конфигурации конвертера."""
