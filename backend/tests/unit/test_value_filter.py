"""Value pre-screen for the hunt (ADR-023): a tunable, versioned, OFF-by-default filter that keeps
only names that look undervalued (high UndervaluationScore) and records the score for later
value-vs-algo analysis. Unscored names (ETFs / unmapped tickers) pass through on technicals only,
exactly like the ADR-017 fundamentals veto. The score provider is injected — no network in CI."""

from datetime import date

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.lab.value_filter import (
    ValueGateConfig,
    ValueScreen,
    make_value_provider,
    screen_value,
)
from app.research.valuation import UndervaluationScore
from app.research.valuation.intrinsic_value import DcfAssumptions


def _score(score: float | None, *, margin_of_safety: float | None = 0.1) -> UndervaluationScore:
    return UndervaluationScore(
        symbol="AAA",
        cik=1,
        entity_name="Acme",
        fiscal_year=2024,
        form="10-K",
        accession_number="a-2024",
        source_url="https://sec.gov/x",
        current_price=50.0,
        pe_ratio=10.0,
        pe_percentile=0.3,
        ps_ratio=2.0,
        ps_percentile=0.3,
        intrinsic_value_per_share=55.0,
        margin_of_safety=margin_of_safety,
        growth_rate_used=0.03,
        fcf_is_net_income_proxy=False,
        score=score,
        flags=[],
    )


# --- ValueGateConfig ---------------------------------------------------------------------------


def test_value_gate_config_defaults_are_permissive() -> None:
    cfg = ValueGateConfig()
    assert cfg.min_score == 0.5
    assert cfg.keep_unscored is True
    assert cfg.require_margin_of_safety is False


def test_value_gate_config_version_hash_changes_with_thresholds() -> None:
    assert ValueGateConfig().version_hash == ValueGateConfig().version_hash
    assert (
        ValueGateConfig(min_score=0.5).version_hash != ValueGateConfig(min_score=0.6).version_hash
    )


# --- screen_value ------------------------------------------------------------------------------


def test_screen_keeps_a_name_at_or_above_min_score() -> None:
    screen = screen_value(_score(0.6), ValueGateConfig(min_score=0.5))
    assert isinstance(screen, ValueScreen)
    assert screen.passed is True
    assert screen.score == 0.6
    assert screen.reasons == []


def test_screen_keeps_a_name_exactly_at_min_score() -> None:
    # Boundary: >= min_score passes (cheapness score, higher is cheaper).
    assert screen_value(_score(0.5), ValueGateConfig(min_score=0.5)).passed is True


def test_screen_rejects_a_name_below_min_score_with_a_reason() -> None:
    screen = screen_value(_score(0.4), ValueGateConfig(min_score=0.5))
    assert screen.passed is False
    assert screen.score == 0.4
    assert any("0.40" in r and "0.50" in r for r in screen.reasons)


def test_none_score_object_passes_when_keep_unscored_true() -> None:
    # ETF / unmapped ticker -> no score at all -> technicals only.
    screen = screen_value(None, ValueGateConfig(keep_unscored=True))
    assert screen.passed is True
    assert screen.score is None
    assert screen.reasons == []


def test_none_score_object_is_rejected_when_keep_unscored_false() -> None:
    screen = screen_value(None, ValueGateConfig(keep_unscored=False))
    assert screen.passed is False
    assert any("no undervaluation score" in r.lower() for r in screen.reasons)


def test_score_object_with_none_score_routes_through_keep_unscored() -> None:
    # A scored object whose composite is uncomputable (no components) is treated as unscored.
    assert screen_value(_score(None), ValueGateConfig(keep_unscored=True)).passed is True
    assert screen_value(_score(None), ValueGateConfig(keep_unscored=False)).passed is False


def test_require_margin_of_safety_rejects_non_positive_mos() -> None:
    cfg = ValueGateConfig(min_score=0.0, require_margin_of_safety=True)
    assert screen_value(_score(0.9, margin_of_safety=0.2), cfg).passed is True
    neg = screen_value(_score(0.9, margin_of_safety=-0.1), cfg)
    assert neg.passed is False
    assert any("margin of safety" in r.lower() for r in neg.reasons)
    none = screen_value(_score(0.9, margin_of_safety=None), cfg)
    assert none.passed is False


# --- make_value_provider -----------------------------------------------------------------------


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


def test_provider_composes_history_price_join_and_score() -> None:
    closes = [
        (date(2023, 12, 29), 40.0),
        (date(2024, 12, 31), 60.0),
        (date(2025, 6, 30), 45.0),
    ]
    provider = make_value_provider(
        lambda s: _history(),
        lambda s: closes,
        assumptions=DcfAssumptions(),
    )
    result = provider("AAA")
    assert isinstance(result, UndervaluationScore)
    assert result.symbol == "AAA"
    assert result.current_price == 45.0  # last close = the "current" price


def test_provider_returns_none_when_history_lookup_fails() -> None:
    def raises(_symbol: str) -> FundamentalsHistory:
        raise ValueError("no CIK for ETF")

    provider = make_value_provider(raises, lambda s: [(date(2024, 1, 1), 10.0)])
    assert provider("SPY") is None


def test_provider_returns_none_when_no_prices() -> None:
    provider = make_value_provider(lambda s: _history(), lambda s: [])
    assert provider("AAA") is None
