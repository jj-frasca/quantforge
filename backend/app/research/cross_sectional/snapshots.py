"""Immutable static-score snapshots for cross-sectional factor identity (ADR-143)."""

from collections.abc import Iterator, Mapping, Sequence
from math import isfinite
from types import MappingProxyType
from typing import Never


class FrozenScoreSnapshot(Mapping[str, float]):
    """An insertion-ordered, JSON-object-compatible mapping with no mutation surface."""

    __slots__ = ("_keys", "_values")

    def __init__(self, values: Mapping[str, float]) -> None:
        copied = dict(values)
        self._keys = tuple(copied)
        self._values = MappingProxyType(copied)

    def __getitem__(self, key: str) -> float:
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._keys)

    def __len__(self) -> int:
        return len(self._keys)

    def __repr__(self) -> str:
        return repr(dict(self.items()))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Mapping):
            return False
        return list(self.items()) == list(other.items())

    @staticmethod
    def _immutable() -> Never:
        raise TypeError("fundamental score snapshot is immutable")

    def __setitem__(self, key: str, value: float) -> Never:
        self._immutable()

    def __delitem__(self, key: str) -> Never:
        self._immutable()

    def clear(self) -> Never:
        self._immutable()

    def pop(self, key: str, default: object = None) -> Never:
        self._immutable()

    def popitem(self) -> Never:
        self._immutable()

    def setdefault(self, key: str, default: float = 0.0) -> Never:
        self._immutable()

    def update(self, *args: object, **kwargs: object) -> Never:
        self._immutable()

    def __ior__(self, other: object) -> Never:
        self._immutable()


def freeze_score_snapshot(
    scores: Mapping[str, float] | None, universe_symbols: Sequence[str]
) -> FrozenScoreSnapshot | None:
    """Validate a finite panel-ordered subset and return a defensive immutable copy."""
    if scores is None:
        return None
    keys = list(scores)
    expected_keys = [symbol for symbol in universe_symbols if symbol in scores]
    if keys != expected_keys:
        raise ValueError("fundamental score keys must follow frozen universe order")
    values = {symbol: float(scores[symbol]) for symbol in keys}
    if not all(isfinite(value) for value in values.values()):
        raise ValueError("fundamental scores must be finite")
    return FrozenScoreSnapshot(values)
