from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd


class BaseStrategy(ABC):
    """Signal generator contract (backtesting-spec.md §2).

    Subclasses produce a position-weight series in [-1, 1] with NO look-ahead: the signal at
    time t may use only data up to and including t. ``research_citations`` is never empty.
    """

    name: ClassVar[str]
    research_citations: ClassVar[list[str]]

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a float position weight in [-1, 1] per bar, indexed like ``data``."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, object]:
        """The strategy's parameters (feeds the ExperimentManifest parameter hash)."""
        ...
