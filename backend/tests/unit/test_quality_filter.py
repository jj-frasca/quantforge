"""Quality pre-screen for the hunt (ADR-029 4b). The honest way to make the ADR-018 universe-
deflation bar clearable is to test FEWER, better-motivated hypotheses — not to lower the bar
(ADR-033 refuses to shrink N artificially). Screening the universe on an ex-ante business-quality
criterion genuinely reduces the number of hypotheses tested, so the smaller N is earned. The rubric
is fixed in advance and versioned; it is never tuned to produce graduates."""

import pytest

from app.research.fundamentals.record import FundamentalRecord
from app.research.lab.quality_filter import (
    QualityGateConfig,
    make_quality_provider,
    screen_quality,
)


def _record(symbol: str, *, quality: float | None = 0.7, f_score: int = 6) -> FundamentalRecord:
    return FundamentalRecord(
        symbol=symbol,
        cik=1,
        fiscal_year=2025,
        quality_score=quality,
        value_score=None,
        combined_score=None,
        f_score=f_score,
        gross_profitability=0.3,
    )


def test_a_high_quality_name_clears_the_screen() -> None:
    screen = screen_quality(_record("GOOD", quality=0.8), QualityGateConfig(min_quality_score=0.5))
    assert screen.passed
    assert screen.score == 0.8
    assert screen.reasons == []


def test_a_low_quality_name_is_screened_out_with_a_cited_reason() -> None:
    screen = screen_quality(_record("WEAK", quality=0.2), QualityGateConfig(min_quality_score=0.5))
    assert not screen.passed
    assert "0.20" in screen.reasons[0] and "0.50" in screen.reasons[0]


def test_an_unscored_name_passes_by_default() -> None:
    # An ETF or an unmapped ticker has no 10-K. It is hunted on technicals only — never vetoed for
    # being unscorable, exactly like the ADR-017 fundamentals veto and the ADR-023 value screen.
    screen = screen_quality(None, QualityGateConfig())
    assert screen.passed
    assert screen.score is None


def test_an_unscored_name_can_be_excluded_for_a_fundamentals_required_run() -> None:
    screen = screen_quality(None, QualityGateConfig(keep_unscored=False))
    assert not screen.passed
    assert "no quality score" in screen.reasons[0]


def test_a_record_whose_quality_is_none_is_treated_as_unscored() -> None:
    screen = screen_quality(_record("NOQ", quality=None), QualityGateConfig(keep_unscored=False))
    assert not screen.passed
    assert screen.score is None


def test_an_optional_f_score_floor_screens_a_weak_balance_sheet() -> None:
    config = QualityGateConfig(min_quality_score=0.0, min_f_score=5)
    assert screen_quality(_record("STRONG", f_score=7), config).passed
    weak = screen_quality(_record("WEAK", f_score=3), config)
    assert not weak.passed
    assert "F-score 3" in weak.reasons[0]


def test_the_f_score_floor_is_off_by_default() -> None:
    assert screen_quality(
        _record("ANY", f_score=0), QualityGateConfig(min_quality_score=0.0)
    ).passed


def test_both_failures_are_reported_not_just_the_first() -> None:
    config = QualityGateConfig(min_quality_score=0.9, min_f_score=8)
    screen = screen_quality(_record("BAD", quality=0.1, f_score=1), config)
    assert len(screen.reasons) == 2


def test_the_config_is_versioned_so_a_filtered_universe_is_reproducible() -> None:
    a = QualityGateConfig(min_quality_score=0.5)
    b = QualityGateConfig(min_quality_score=0.6)
    assert a.version_hash == QualityGateConfig(min_quality_score=0.5).version_hash
    assert a.version_hash != b.version_hash


def test_provider_looks_a_symbol_up_in_the_fundamentals_pool() -> None:
    provider = make_quality_provider([_record("AAA", quality=0.8), _record("BBB", quality=0.2)])
    assert provider("AAA") is not None and provider("AAA").quality_score == 0.8
    assert provider("BBB").quality_score == 0.2


def test_provider_returns_none_for_a_symbol_absent_from_the_pool() -> None:
    provider = make_quality_provider([_record("AAA")])
    assert provider("QQQ") is None  # an ETF the EDGAR sweep never scored


def test_provider_is_case_insensitive_on_the_symbol() -> None:
    provider = make_quality_provider([_record("AAA")])
    assert provider("aaa") is not None


def test_provider_keeps_the_newest_filing_when_a_symbol_appears_twice() -> None:
    old = _record("AAA", quality=0.2)
    new = _record("AAA", quality=0.9).model_copy(update={"fiscal_year": 2026})
    provider = make_quality_provider([old, new])
    assert provider("AAA").quality_score == pytest.approx(0.9)
