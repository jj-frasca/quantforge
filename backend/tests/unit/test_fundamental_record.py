"""ADR-029 Layer 3: the FundamentalRecord contract + pure compute/merge/leaderboard for the
fundamental discovery sweep. A record is the per-company as-of snapshot the sweep writes; merge
dedups by CIK keeping the newest filing (bounding the pool to one row per company); the leaderboard
ranks the "genuinely good, reasonably priced" companies. All pure — the network lives in the script."""

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import (
    FundamentalRecord,
    compute_fundamental_record,
    merge_fundamental_records,
    rank_fundamentals,
)


def _year(fy: int, **overrides: float | None) -> AnnualFundamentals:
    base: dict[str, float | None] = {
        "fiscal_year": fy,
        "revenue": 1000.0,
        "net_income": 100.0,
        "shares_diluted": 50.0,
        "total_assets": 2000.0,
        "total_current_assets": 800.0,
        "total_current_liabilities": 400.0,
        "long_term_debt": 500.0,
        "gross_profit": 400.0,
        "operating_cash_flow": 150.0,
        "retained_earnings": 300.0,
        "total_equity": 1200.0,
    }
    base.update(overrides)
    return AnnualFundamentals(**base)  # type: ignore[arg-type]


def _history(
    symbol: str = "TEST", cik: int = 320193, *years: AnnualFundamentals
) -> FundamentalsHistory:
    return FundamentalsHistory(
        symbol=symbol,
        cik=cik,
        entity_name="Test Corp",
        form="10-K",
        accession_number="0000000000-00-000000",
        source_url="https://www.sec.gov/",
        years=tuple(years),
    )


def _record(
    symbol: str,
    cik: int,
    fy: int,
    *,
    quality: float | None = 0.5,
    value: float | None = None,
    combined: float | None = None,
) -> FundamentalRecord:
    return FundamentalRecord(
        symbol=symbol,
        cik=cik,
        fiscal_year=fy,
        quality_score=quality,
        value_score=value,
        combined_score=combined,
        f_score=5,
        gross_profitability=0.2,
    )


# ---- compute_fundamental_record ------------------------------------------------------------------


def test_compute_without_price_yields_quality_only() -> None:
    hist = _history("AAA", 1, _year(2023), _year(2024))
    rec = compute_fundamental_record(hist)
    assert rec.symbol == "AAA" and rec.cik == 1 and rec.fiscal_year == 2024
    assert rec.quality_score is not None
    assert rec.value_score is None  # no price -> no valuation leg
    assert rec.combined_score is None
    assert rec.f_score >= 1


def test_compute_with_price_adds_value_and_combined() -> None:
    hist = _history("BBB", 2, _year(2023), _year(2024))
    rec = compute_fundamental_record(hist, price=10.0)
    assert rec.quality_score is not None
    # value may or may not be computable from these inputs, but combined is defined iff both exist.
    if rec.value_score is not None:
        assert rec.combined_score == rec.quality_score * rec.value_score
    else:
        assert rec.combined_score is None


def test_compute_empty_history_is_all_none_but_records_identity() -> None:
    hist = _history("EMPTY", 9)
    rec = compute_fundamental_record(hist)
    assert rec.symbol == "EMPTY" and rec.cik == 9
    assert rec.quality_score is None and rec.combined_score is None
    assert "no fundamentals history" in rec.flags


# ---- merge_fundamental_records -------------------------------------------------------------------


def test_merge_dedups_by_cik_keeping_newest_filing() -> None:
    old = _record("AAA", 1, 2022)
    new = _record("AAA", 1, 2024)
    merged = merge_fundamental_records([old], [new])
    assert len(merged) == 1 and merged[0].fiscal_year == 2024


def test_merge_keeps_existing_when_incoming_is_older() -> None:
    existing = _record("AAA", 1, 2024)
    stale = _record("AAA", 1, 2020)
    merged = merge_fundamental_records([existing], [stale])
    assert merged[0].fiscal_year == 2024  # never regress to an older filing


def test_merge_incoming_wins_on_equal_fiscal_year() -> None:
    old = _record("AAA", 1, 2024, quality=0.1)
    fresh = _record("AAA", 1, 2024, quality=0.9)
    merged = merge_fundamental_records([old], [fresh])
    assert merged[0].quality_score == 0.9  # idempotent re-run refreshes in place


def test_merge_unions_distinct_ciks() -> None:
    merged = merge_fundamental_records([_record("AAA", 1, 2024)], [_record("BBB", 2, 2024)])
    assert {r.cik for r in merged} == {1, 2}


# ---- rank_fundamentals (leaderboard) -------------------------------------------------------------


def test_rank_by_combined_orders_desc_and_drops_none() -> None:
    records = [
        _record("LOW", 1, 2024, combined=0.1),
        _record("HIGH", 2, 2024, combined=0.9),
        _record("MID", 3, 2024, combined=0.5),
        _record("NONE", 4, 2024, combined=None),
    ]
    ranked = rank_fundamentals(records, by="combined")
    assert [r.symbol for r in ranked] == ["HIGH", "MID", "LOW"]  # NONE excluded


def test_rank_by_quality_respects_top_n() -> None:
    records = [_record(f"S{i}", i, 2024, quality=i / 10.0) for i in range(1, 6)]
    ranked = rank_fundamentals(records, by="quality", top=2)
    assert [r.symbol for r in ranked] == ["S5", "S4"]


def test_rank_empty_when_all_scores_none() -> None:
    records = [_record("A", 1, 2024, quality=None, combined=None)]
    assert rank_fundamentals(records, by="quality") == []
