"""Defensive deep-freeze helpers for persisted cross-sectional claims (ADR-145)."""

from collections.abc import Mapping
from typing import Never, SupportsIndex

from pydantic import BaseModel


class FrozenClaimList(list[object]):
    """A JSON-array-compatible list whose ordinary mutation surface is disabled."""

    @staticmethod
    def _immutable() -> Never:
        raise AttributeError("cross-sectional experiment claim graph is immutable")

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


class FrozenClaimDict(dict[object, object]):
    """A JSON-object-compatible dictionary whose ordinary mutation surface is disabled."""

    @staticmethod
    def _immutable() -> Never:
        raise TypeError("cross-sectional experiment claim graph is immutable")

    def __setitem__(self, key: object, value: object) -> Never:
        self._immutable()

    def __delitem__(self, key: object) -> Never:
        self._immutable()

    def __ior__(self, other: object) -> Never:  # type: ignore[misc]
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def pop(self, key: object, default: object = None) -> Never:
        self._immutable()

    def popitem(self) -> Never:
        self._immutable()

    def setdefault(self, key: object, default: object = None) -> Never:
        self._immutable()

    def update(self, *args: object, **kwargs: object) -> Never:
        self._immutable()


def _freeze_value(value: object) -> object:
    if isinstance(value, BaseModel):
        return freeze_claim_model(value)
    if isinstance(value, Mapping):
        return FrozenClaimDict({key: _freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return FrozenClaimList([_freeze_value(item) for item in value])
    return value


def freeze_claim_model(model: BaseModel) -> BaseModel:
    """Reconstruct and recursively freeze a Pydantic model without mutating caller-owned state."""
    copied = type(model).model_validate(model.model_dump(round_trip=True))
    for field_name in type(copied).model_fields:
        object.__setattr__(copied, field_name, _freeze_value(getattr(copied, field_name)))
    return copied
