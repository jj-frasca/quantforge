"""Pure handling of checked-in universe files (ADR-026 universe expansion).

Universe files are one uppercase ticker per line. This module is the single tested place that
turns those files into clean symbol lists, so scripts and the hunt never re-implement the
strip/upper/dedup/drop-blanks dance ad hoc.

Notes:
    - ``load_universe`` preserves first-seen order (the files are already sorted; order is kept
      so a caller can rely on file order if it wants).
    - ``merge_universes`` returns the sorted, de-duped union — the canonical form for a combined
      seed universe.
"""

import re
from collections.abc import Iterable
from pathlib import Path

# yfinance tickers: 1-5 uppercase letters, optional class suffix (BRK.B / BRK-B). Kept deliberately
# strict so junk lines (lowercase, spaces, punctuation, over-long strings) are rejected as garbage.
_TICKER_RE = re.compile(r"^[A-Z]{1,5}([.-][A-Z])?$")


def is_well_formed_ticker(ticker: str) -> bool:
    """True if ``ticker`` looks like a normalized US equity/ETF symbol (already upper, no spaces)."""
    return bool(_TICKER_RE.match(ticker))


def _normalize(lines: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        symbol = line.strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            out.append(symbol)
    return out


def load_universe(path: Path | str) -> list[str]:
    """Read a universe file → uppercased, stripped, de-duped symbols with blanks dropped."""
    return _normalize(Path(path).read_text().splitlines())


def merge_universes(paths: Iterable[Path | str]) -> list[str]:
    """Merge universe files into the sorted, de-duped union of their symbols."""
    combined: set[str] = set()
    for path in paths:
        combined.update(load_universe(path))
    return sorted(combined)
