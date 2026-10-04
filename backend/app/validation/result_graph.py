"""JSON-shaped immutable containers for validation result graphs (ADR-159)."""

from typing import Never, SupportsIndex


class FrozenResultList(list[object]):
    """A JSON-array-compatible list with its public mutation surface disabled."""

    @staticmethod
    def _immutable() -> Never:
        raise AttributeError("validation result graph is immutable")

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


class FrozenResultDict(dict[str, object]):
    """A JSON-object-compatible dictionary with public mutation disabled."""

    @staticmethod
    def _immutable() -> Never:
        raise TypeError("validation result graph is immutable")

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
