"""Defensive JSON-compatible values for canonical data-model evidence."""

import math
from collections.abc import Mapping
from typing import Never, SupportsIndex


class FrozenJsonList(list[object]):
    @staticmethod
    def _immutable() -> Never:
        raise AttributeError("claim JSON evidence is immutable")

    def __setitem__(self, key: object, value: object) -> Never:
        self._immutable()

    def __delitem__(self, key: object) -> Never:
        self._immutable()

    def __iadd__(self, value: object) -> Never:  # type: ignore[misc]
        self._immutable()

    def __imul__(self, value: object) -> Never:
        self._immutable()

    def append(self, value: object) -> Never:
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def extend(self, values: object) -> Never:
        self._immutable()

    def insert(self, index: SupportsIndex, value: object) -> Never:
        self._immutable()

    def pop(self, index: SupportsIndex = -1) -> Never:
        self._immutable()

    def remove(self, value: object) -> Never:
        self._immutable()

    def reverse(self) -> Never:
        self._immutable()

    def sort(self, *args: object, **kwargs: object) -> Never:
        self._immutable()


class FrozenJsonDict(dict[str, object]):
    @staticmethod
    def _immutable() -> Never:
        raise TypeError("claim JSON evidence is immutable")

    def __setitem__(self, key: str, value: object) -> Never:
        self._immutable()

    def __delitem__(self, key: str) -> Never:
        self._immutable()

    def __ior__(self, other: object) -> Never:  # type: ignore[misc]
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def pop(self, key: str, default: object = None) -> Never:
        self._immutable()

    def popitem(self) -> Never:
        self._immutable()

    def setdefault(self, key: str, default: object = None) -> Never:
        self._immutable()

    def update(self, *args: object, **kwargs: object) -> Never:
        self._immutable()


def freeze_json(value: object) -> object:
    """Defensively copy finite JSON data into serialization-compatible frozen containers."""
    if value is None or isinstance(value, (bool, str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("claim JSON floats must be finite")
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("claim JSON object keys must be strings")
        return FrozenJsonDict({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenJsonList([freeze_json(item) for item in value])
    raise ValueError("claim evidence must contain only JSON-compatible values")
