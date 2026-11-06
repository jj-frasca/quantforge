"""Retained frozen-config evidence, not portfolio alpha (ADR-413).

Paired controls use each stored score's own horizon. Lifecycle stopping and
shared calendars preclude independent/common-horizon inference from these rows.
"""

from collections.abc import Sequence
from statistics import mean, median
from typing import Any

from app.research.lab.paper import PaperPosition


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    measured = [row for row in rows if row["forward_bars"] is not None and row["forward_bars"] > 0]
    result: dict[str, Any] = {
        "n_positions": len(rows),
        "n_measured": len(measured),
        "n_missing_score": sum(row["forward_bars"] is None for row in rows),
        "n_zero_bar": sum(row["forward_bars"] == 0 for row in rows),
        "n_mature": sum(row["forward_bars"] >= 126 for row in measured),
        "n_zero_turnover": sum(row["forward_trades"] == 0 for row in measured),
        "n_curve": sum(row["curve_available"] for row in measured),
        "n_lineage": sum(row["lineage_available"] for row in measured),
        "n_path_nonzero": sum(row["path_nonzero"] is True for row in measured),
        "n_path_unknown": sum(row["path_nonzero"] is None for row in measured),
        "n_stored_sharpe_beat": sum(row["stored_sharpe_beat"] for row in measured),
        "n_positive_return_difference": sum(row["return_difference"] > 0 for row in measured),
        "n_positive_sharpe_difference": sum(row["sharpe_difference"] > 0 for row in measured),
        "min_forward_bars": min((row["forward_bars"] for row in measured), default=None),
        "max_forward_bars": max((row["forward_bars"] for row in measured), default=None),
    }
    for metric in ("return_difference", "sharpe_difference"):
        values = [row[metric] for row in measured]
        result[f"median_{metric}"] = median(values) if values else None
        result[f"mean_{metric}"] = mean(values) if values else None
    return result


def summarize_paper_evidence(positions: Sequence[PaperPosition]) -> dict[str, Any]:
    """Describe every supplied position without selecting winners or changing claims.

    Stored beat flags retain their historical meaning. Zero turnover does not
    imply zero exposure; missing curves cannot establish an all-zero return path.
    Even a measured all-zero path does not prove flat holdings (ADR-361).
    """
    rows: list[dict[str, Any]] = []
    for original in positions:
        position = PaperPosition.model_validate(original.model_dump())
        score = position.score
        measured = score is not None and score.forward_bars > 0
        curve = score.forward_equity if score is not None else []
        previous = 1.0
        path_nonzero: bool | None = None
        if curve:
            path_nonzero = False
            for point in curve:
                if point.strategy_equity != previous:
                    path_nonzero = True
                previous = point.strategy_equity
        rows.append(
            {
                "ordinal": len(rows),
                "symbol": position.symbol,
                "strategy_name": position.strategy_name,
                "parameters": dict(position.parameters),
                "frozen_at": position.frozen_at.isoformat(),
                "status": position.status,
                "closed_at": position.closed_at.isoformat() if position.closed_at else None,
                "as_of": score.as_of.isoformat() if score else None,
                "deflation_verdict": position.survives_universe_deflation,
                "forward_bars": score.forward_bars if score else None,
                "forward_trades": score.forward_trades if score else None,
                "curve_available": bool(curve),
                "lineage_available": score is not None and score.evidence is not None,
                "path_nonzero": path_nonzero,
                "strategy_return": score.forward_return if measured and score else None,
                "hold_return": score.buy_and_hold_return if measured and score else None,
                "return_difference": (
                    score.forward_return - score.buy_and_hold_return if measured and score else None
                ),
                "sharpe_difference": (
                    score.forward_sharpe - score.buy_and_hold_sharpe if measured and score else None
                ),
                "stored_sharpe_beat": score.beats_buy_and_hold if measured and score else None,
            }
        )
    cohorts = {
        label: _summary([row for row in rows if row["deflation_verdict"] is verdict])
        for label, verdict in (("survivors", True), ("non_survivors", False), ("unknown", None))
    }
    return {
        "method": "retained-paper-config-description-v1",
        "interpretation": "retrospective descriptive configuration scores; not account alpha",
        "costs": (
            "Current producer: 0.001 per unit internal turnover; historical rate not stored. "
            "Same-name holding benchmark is gross; account entry/switch/borrow costs unverified."
        ),
        "geometry": "Each original post-freeze cutoff; lifecycle-truncated unequal horizons.",
        "populations": {
            "all": _summary(rows),
            "open": _summary([row for row in rows if row["status"] == "open"]),
            "closed": _summary([row for row in rows if row["status"] == "closed"]),
        },
        "cohorts": cohorts,
        "adr033_trigger_met": (
            cohorts["survivors"]["n_mature"] >= 20 and cohorts["non_survivors"]["n_mature"] >= 20
        ),
        "rows": rows,
    }
