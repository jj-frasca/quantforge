"""Fundamental quality scoring (ADR-029 Layer 2): cited quality factors over EDGAR fundamentals —
Piotroski F-Score, Novy-Marx gross profitability, a leverage/liquidity safety proxy — composited
into a QualityScore that complements the ADR-022 UndervaluationScore (value). Pure + network-free;
flags potential, never guarantees (CLAUDE.md rule 6)."""

from app.research.fundamentals.quality import (
    FScore,
    QualityScore,
    SafetyScore,
    financial_safety,
    gross_profitability,
    piotroski_f_score,
    quality_score,
)
from app.research.fundamentals.record import (
    FundamentalRecord,
    compute_fundamental_record,
    merge_fundamental_records,
    rank_fundamentals,
)

__all__ = [
    "FScore",
    "FundamentalRecord",
    "QualityScore",
    "SafetyScore",
    "compute_fundamental_record",
    "financial_safety",
    "gross_profitability",
    "merge_fundamental_records",
    "piotroski_f_score",
    "quality_score",
    "rank_fundamentals",
]
