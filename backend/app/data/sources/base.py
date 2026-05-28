from abc import ABC, abstractmethod
from datetime import datetime
from typing import ClassVar

from app.data.models import PriceBar, Source


class DataSourceAdapter(ABC):
    """Contract every market-data vendor implements (ADR-005).

    Raw vendor output is normalized to canonical PriceBars at ingestion — never at query
    time — and vendor-specific shapes never leak past this boundary. Subclasses set
    ``source`` and ``adapter_version`` (the latter is pinned into the ExperimentManifest
    for reproducibility).
    """

    source: ClassVar[Source]
    adapter_version: ClassVar[str]

    @abstractmethod
    def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
        """Return canonical PriceBars for the half-open range ``[start, end)``.

        Implementations fetch raw vendor data and normalize it here.
        """
        ...
