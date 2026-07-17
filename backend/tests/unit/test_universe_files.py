"""Universe-file format handling (ADR-026 universe expansion): reading the checked-in
one-ticker-per-line files must be a tested unit, not ad-hoc string munging in scripts. Load
normalizes (strip/upper/dedup/drop-blanks); merge is the sorted, de-duped union across files.
Format validation guards against garbage tickers slipping into the seed universe."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.universe_files import (
    is_well_formed_ticker,
    load_universe,
    merge_universes,
)


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines))
    return path


def test_load_universe_strips_uppercases_and_drops_blanks(tmp_path: Path) -> None:
    path = _write(tmp_path / "u.txt", ["aapl", "  MSFT  ", "", "  ", "nvda"])
    assert load_universe(path) == ["AAPL", "MSFT", "NVDA"]


def test_load_universe_dedups_preserving_first_occurrence(tmp_path: Path) -> None:
    path = _write(tmp_path / "u.txt", ["AAPL", "msft", "AAPL", "MSFT", "aapl"])
    assert load_universe(path) == ["AAPL", "MSFT"]


def test_load_universe_accepts_str_path(tmp_path: Path) -> None:
    path = _write(tmp_path / "u.txt", ["spy", "qqq"])
    assert load_universe(str(path)) == ["SPY", "QQQ"]


def test_load_universe_handles_trailing_newline_and_crlf(tmp_path: Path) -> None:
    path = tmp_path / "u.txt"
    path.write_text("AAPL\r\nMSFT\r\n\r\n")
    assert load_universe(path) == ["AAPL", "MSFT"]


def test_load_universe_empty_file_is_empty_list(tmp_path: Path) -> None:
    path = _write(tmp_path / "empty.txt", [])
    assert load_universe(path) == []


def test_merge_universes_is_sorted_deduped_union(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.txt", ["MSFT", "aapl", "nvda"])
    b = _write(tmp_path / "b.txt", ["nvda", "amzn", "AAPL"])
    assert merge_universes([a, b]) == ["AAPL", "AMZN", "MSFT", "NVDA"]


def test_merge_universes_no_paths_is_empty() -> None:
    assert merge_universes([]) == []


def test_merge_universes_single_path_matches_sorted_load(tmp_path: Path) -> None:
    a = _write(tmp_path / "a.txt", ["nvda", "aapl", "aapl"])
    assert merge_universes([a]) == ["AAPL", "NVDA"]


@pytest.mark.parametrize(
    "ticker",
    ["A", "AAPL", "BRK.B", "BRK-B", "GOOGL", "V", "BF.B", "SPY", "IWM", "SPXL"],
)
def test_is_well_formed_ticker_accepts_real_tickers(ticker: str) -> None:
    assert is_well_formed_ticker(ticker) is True


@pytest.mark.parametrize(
    "ticker",
    ["", "aapl", "  ", "TOOLONGTICKER", "A B", "AA_PP", "$MSFT", "A/B", "123456789"],
)
def test_is_well_formed_ticker_rejects_garbage(ticker: str) -> None:
    assert is_well_formed_ticker(ticker) is False


@given(st.text())
def test_is_well_formed_ticker_never_raises(text: str) -> None:
    assert isinstance(is_well_formed_ticker(text), bool)


@given(
    st.lists(
        st.sampled_from(["AAPL", "MSFT", "NVDA", "SPY", "QQQ", "AMZN", "GOOGL"]),
        max_size=20,
    )
)
def test_merge_universes_output_is_sorted_and_unique(symbols: list[str]) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "u.txt"
        path.write_text("\n".join(symbols))
        out = merge_universes([path])
    assert out == sorted(set(symbols))
