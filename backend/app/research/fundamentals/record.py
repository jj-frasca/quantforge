"""FundamentalRecord: the per-company as-of snapshot the fundamental discovery sweep writes
(ADR-029 Layer 3), plus the pure compute / merge / leaderboard logic around it.

The sweep enumerates the SEC CIK universe, fetches each company's `FundamentalsHistory` (EDGAR,
free), computes a `FundamentalRecord`, and appends it to a sharded output; a consolidation job
`merge_fundamental_records` folds every shard into `data/fundamentals_pool.json`, deduping by CIK
and keeping the newest filing — which bounds the pool to one row per company. `rank_fundamentals`
is the leaderboard: the genuinely good, reasonably priced companies. All network-free (the network
lives in the sweep script); every score cites its filing and flags potential, never guarantees."""

from pydantic import BaseModel, ConfigDict

from app.data.fundamentals import FundamentalsHistory
from app.research.fundamentals.quality import quality_score
from app.research.valuation.score import score_valuation

_RANK_FIELDS = {
    "combined": "combined_score",
    "quality": "quality_score",
    "value": "value_score",
}


class FundamentalRecord(BaseModel):
    """One company's fundamental snapshot as of its latest filing (ADR-029). `quality_score` is the
    ADR-029 composite; `value_score` is the ADR-022 UndervaluationScore (only when a price was
    available); `combined_score` = quality * value when BOTH exist (good AND cheap), else None.
    Raw legs (`f_score`, `gross_profitability`) and `flags` travel with the row for legibility."""

    model_config = ConfigDict(frozen=True)

    symbol: str
    cik: int
    fiscal_year: int  # the as-of year of the latest filing this record summarizes
    quality_score: float | None
    value_score: float | None
    combined_score: float | None
    f_score: int
    gross_profitability: float | None
    flags: list[str] = []


def compute_fundamental_record(
    history: FundamentalsHistory, price: float | None = None
) -> FundamentalRecord:
    """Compute a FundamentalRecord from a company's history (and optionally its latest price). Quality
    is always computed from EDGAR alone; value is added only when `price` is supplied, and `combined`
    only when both quality and value are present. Empty history yields an all-None record that still
    records the company's identity (and flags why nothing was computable)."""
    q = quality_score(history)
    flags = list(q.flags)

    value_score: float | None = None
    if price is not None and history.years:
        valuation = score_valuation(history, price)
        value_score = valuation.score
        flags.extend(valuation.flags)

    combined: float | None = None
    if q.score is not None and value_score is not None:
        combined = q.score * value_score

    fiscal_year = history.years[-1].fiscal_year if history.years else 0
    return FundamentalRecord(
        symbol=history.symbol,
        cik=history.cik,
        fiscal_year=fiscal_year,
        quality_score=q.score,
        value_score=value_score,
        combined_score=combined,
        f_score=q.f_score.score,
        gross_profitability=q.gross_profitability,
        flags=flags,
    )


def merge_fundamental_records(
    existing: list[FundamentalRecord], incoming: list[FundamentalRecord]
) -> list[FundamentalRecord]:
    """Fold `incoming` into `existing`, deduping by CIK: keep whichever record has the newer filing
    year, and on a tie let `incoming` win (so a re-run of a shard refreshes in place — idempotent).
    Deduping by CIK bounds the pool to one row per company (ADR-029 / ADR-026 bounding)."""
    by_cik: dict[int, FundamentalRecord] = {r.cik: r for r in existing}
    for rec in incoming:
        current = by_cik.get(rec.cik)
        if current is None or rec.fiscal_year >= current.fiscal_year:
            by_cik[rec.cik] = rec
    return list(by_cik.values())


def rank_fundamentals(
    records: list[FundamentalRecord], *, by: str = "combined", top: int | None = None
) -> list[FundamentalRecord]:
    """Leaderboard: rank `records` descending by the `by` score ("combined" | "quality" | "value"),
    dropping rows whose chosen score is None. `top` truncates to the best N (None = all)."""
    field = _RANK_FIELDS[by]
    scored = [r for r in records if getattr(r, field) is not None]
    scored.sort(key=lambda r: getattr(r, field), reverse=True)
    return scored[:top] if top is not None else scored
