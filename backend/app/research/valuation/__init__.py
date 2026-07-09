"""Value research engine — undervaluation scoring from EDGAR fundamentals (ADR-022)."""

from app.research.valuation.intrinsic_value import (
    DcfAssumptions,
    IntrinsicValueResult,
    dcf_intrinsic_value,
    estimate_growth,
)
from app.research.valuation.multiples import (
    MultiplesResult,
    compute_multiples,
    percentile_rank,
)
from app.research.valuation.score import UndervaluationScore, score_valuation

__all__ = [
    "DcfAssumptions",
    "IntrinsicValueResult",
    "MultiplesResult",
    "UndervaluationScore",
    "compute_multiples",
    "dcf_intrinsic_value",
    "estimate_growth",
    "percentile_rank",
    "score_valuation",
]
