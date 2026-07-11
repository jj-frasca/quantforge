"""Wire the ADR-023 value engine into the hunt (WP-J): build an injectable `ValueProvider` from an
EDGAR fundamentals-history source + the hunt's own daily price frames, so every candidate gets a
cited `UndervaluationScore` RECORDED without a second network round-trip. Recording is on by
default; the hard gate is opt-in via `--value-screen`. Providers are injected — no network in CI.
"""

from datetime import date, datetime

import pandas as pd
import pytest

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.lab.value_filter import ValueGateConfig
from app.research.lab.value_wiring import (
    cached_frame_provider,
    frame_to_close_series,
    make_hunt_value_provider,
    parse_value_screen,
)
from app.research.valuation import UndervaluationScore


def _frame(prices: list[tuple[str, float]]) -> pd.DataFrame:
    index = pd.DatetimeIndex([datetime.fromisoformat(d) for d in [p[0] for p in prices]], tz="UTC")
    return pd.DataFrame(
        {
            "open": [p[1] for p in prices],
            "high": [p[1] for p in prices],
            "low": [p[1] for p in prices],
            "close": [p[1] for p in prices],
            "volume": [1.0 for _ in prices],
        },
        index=index,
    )


def _history() -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol="AAA",
        cik=1,
        entity_name="Acme",
        form="10-K",
        accession_number="a-2024",
        source_url="https://sec.gov/x",
        years=(
            AnnualFundamentals(
                fiscal_year=2023,
                period_end=date(2023, 12, 31),
                revenue=1000.0,
                eps=4.0,
                shares_diluted=100.0,
                free_cash_flow=500.0,
            ),
            AnnualFundamentals(
                fiscal_year=2024,
                period_end=date(2024, 12, 31),
                revenue=1100.0,
                eps=5.0,
                shares_diluted=100.0,
                free_cash_flow=550.0,
            ),
        ),
    )


# --- frame_to_close_series ---------------------------------------------------------------------


def test_frame_to_close_series_extracts_ascending_date_close_pairs() -> None:
    series = frame_to_close_series(_frame([("2024-01-02", 10.0), ("2024-01-03", 11.0)]))
    assert series == [(date(2024, 1, 2), 10.0), (date(2024, 1, 3), 11.0)]


def test_frame_to_close_series_empty_frame_returns_empty() -> None:
    assert frame_to_close_series(pd.DataFrame()) == []


# --- cached_frame_provider ---------------------------------------------------------------------


def test_cached_frame_provider_fetches_each_symbol_once() -> None:
    calls: list[str] = []

    def raw(symbol: str) -> pd.DataFrame:
        calls.append(symbol)
        return _frame([("2024-01-02", 10.0)])

    cached = cached_frame_provider(raw)
    first = cached("AAA")
    second = cached("AAA")
    cached("BBB")
    assert first is second  # same object -> one fetch, shared by hunt + value provider
    assert calls == ["AAA", "BBB"]


# --- make_hunt_value_provider ------------------------------------------------------------------


def test_make_hunt_value_provider_composes_history_and_frame_into_a_score() -> None:
    frames = {"AAA": _frame([("2023-12-29", 40.0), ("2024-12-31", 60.0), ("2025-06-30", 45.0)])}
    provider = make_hunt_value_provider(lambda s: _history(), lambda s: frames[s])
    result = provider("AAA")
    assert isinstance(result, UndervaluationScore)
    assert result.symbol == "AAA"
    assert result.current_price == 45.0  # last close is the "current" price


def test_make_hunt_value_provider_returns_none_when_frame_provider_raises() -> None:
    def raises(_symbol: str) -> pd.DataFrame:
        raise ValueError("no price data for ETF")

    provider = make_hunt_value_provider(lambda s: _history(), raises)
    assert provider("SPY") is None  # unscored -> hunted on technicals only (never crashes)


def test_make_hunt_value_provider_returns_none_when_frame_is_empty() -> None:
    provider = make_hunt_value_provider(lambda s: _history(), lambda s: pd.DataFrame())
    assert provider("AAA") is None


def test_make_hunt_value_provider_returns_none_when_history_lookup_fails() -> None:
    def raises(_symbol: str) -> FundamentalsHistory:
        raise ValueError("no CIK for ETF")

    provider = make_hunt_value_provider(raises, lambda s: _frame([("2024-01-02", 10.0)]))
    assert provider("SPY") is None


# --- parse_value_screen ------------------------------------------------------------------------


def test_parse_value_screen_absent_records_only() -> None:
    config, rest = parse_value_screen(["AAPL", "MSFT"])
    assert config is None  # recording on, hard gate off
    assert rest == ["AAPL", "MSFT"]


def test_parse_value_screen_flag_alone_uses_permissive_default() -> None:
    config, rest = parse_value_screen(["--value-screen", "AAPL"])
    assert config == ValueGateConfig()
    assert config is not None and config.min_score == 0.5
    assert rest == ["AAPL"]


def test_parse_value_screen_flag_with_min_score_overrides() -> None:
    config, rest = parse_value_screen(["--value-screen", "0.65", "AAPL", "MSFT"])
    assert config is not None and config.min_score == 0.65
    assert rest == ["AAPL", "MSFT"]


def test_parse_value_screen_flag_followed_by_symbol_keeps_default_and_symbol() -> None:
    # A non-float token after the flag is a symbol, not a min_score -> keep it as a symbol.
    config, rest = parse_value_screen(["--value-screen", "TSLA"])
    assert config is not None and config.min_score == 0.5
    assert rest == ["TSLA"]


def test_parse_value_screen_flag_at_end_with_no_following_token() -> None:
    config, rest = parse_value_screen(["AAPL", "--value-screen"])
    assert config is not None and config.min_score == 0.5
    assert rest == ["AAPL"]


def test_parse_value_screen_preserves_universe_txt_path() -> None:
    config, rest = parse_value_screen(["--value-screen", "0.55", "data/universes/sp500.txt"])
    assert config is not None and config.min_score == 0.55
    assert rest == ["data/universes/sp500.txt"]


@pytest.mark.live
def test_live_hunt_value_provider_scores_a_real_symbol() -> None:
    from app.data.sources.edgar import SecEdgarFundamentalsSource

    source = SecEdgarFundamentalsSource(user_agent="QuantForge research jjfrasca10@gmail.com")
    frames = {"AAPL": _frame([(f"{y}-12-31", 150.0 + y) for y in range(2015, 2025)])}
    provider = make_hunt_value_provider(source.fetch_history, lambda s: frames[s])
    result = provider("AAPL")
    assert result is not None
    assert result.symbol == "AAPL"
    assert result.cik == 320193
    assert result.accession_number  # citation present (rule 6)
