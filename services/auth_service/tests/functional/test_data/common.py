"""Общие вспомогательные объекты для тестовых payload."""


class UnsetType:
    """Маркер аргумента, который не должен попадать в payload."""

    __slots__ = ()


UNSET = UnsetType()
