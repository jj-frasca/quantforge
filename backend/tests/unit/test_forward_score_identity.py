"""Standalone forward evidence is defensive and internally coherent (ADR-166)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.models import DataQualityReport
from app.research.cross_sectional.forward import (
    CrossSectionalForwardEquityPoint,
    CrossSectionalForwardScore,
    CrossSectionalPosition,
)
from app.research.dataset import ResearchDatasetEvidence
from app.research.lab.paper import ForwardEquityPoint, ForwardScore, PaperPosition

_POINT_TYPES = [ForwardEquityPoint, CrossSectionalForwardEquityPoint]
_SCORE_TYPES = [ForwardScore, CrossSectionalForwardScore]
_START = datetime(2026, 1, 1, tzinfo=UTC)


def _score_payload(panel: bool) -> dict[str, object]:
    benchmark = "benchmark" if panel else "buy_and_hold"
    return {
        "forward_bars": 1,
        "forward_return": 0.1,
        "forward_sharpe": 1.0,
        f"{benchmark}_return": 0.05,
        f"{benchmark}_sharpe": 0.5,
        f"beats_{benchmark}": True,
        "as_of": _START + timedelta(days=1),
        "forward_equity": [
            {
                "timestamp": _START + timedelta(days=1),
                "strategy_equity": 1.1,
                f"{benchmark}_equity": 1.05,
            }
        ],
    }


def _evidence(symbol: str = "A", revision: str = "a" * 40) -> ResearchDatasetEvidence:
    return ResearchDatasetEvidence(
        quality_report=DataQualityReport(symbol=symbol, source="yfinance", checked_at=_START),
        source="yfinance",
        adapter_version="test",
        start=_START,
        end=_START + timedelta(days=3),
        git_commit_hash=revision,
    )


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_curve_is_defensive_immutable_and_json_compatible(score_type: type) -> None:
    payload = _score_payload(score_type is CrossSectionalForwardScore)
    score = score_type.model_validate(payload)
    before = score.model_dump(mode="json")
    curve = payload["forward_equity"]
    assert isinstance(curve, list)
    curve.clear()
    assert score.model_dump(mode="json") == before
    with pytest.raises(AttributeError, match="immutable"):
        score.forward_equity.clear()
    assert score_type.model_validate_json(score.model_dump_json()).model_dump(mode="json") == before


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
@pytest.mark.parametrize("mutation", ["negative", "nan", "length", "terminal", "future", "naive"])
def test_forward_score_direct_and_unchecked_copy_reject_invalid_intrinsic_evidence(
    score_type: type, mutation: str
) -> None:
    payload = _score_payload(score_type is CrossSectionalForwardScore)
    score = score_type.model_validate(payload)
    if mutation == "negative":
        updates = {"forward_bars": -1}
    elif mutation == "nan":
        updates = {"forward_sharpe": float("nan")}
    elif mutation == "length":
        updates = {"forward_bars": 2}
    elif mutation == "terminal":
        updates = {"forward_return": 0.2}
    elif mutation == "future":
        updates = {"as_of": _START}
    else:
        updates = {"as_of": _START.replace(tzinfo=None)}
    with pytest.raises(ValueError):
        score_type.model_validate(dict(payload, **updates))
    with pytest.raises(ValueError):
        score_type.model_validate(score.model_copy(update=updates))


@pytest.mark.parametrize("point_type", _POINT_TYPES)
@pytest.mark.parametrize(
    "field,value",
    [
        ("strategy_equity", 0.0),
        ("strategy_equity", float("inf")),
        ("timestamp", datetime(2026, 1, 1)),
    ],
)
def test_forward_point_direct_and_unchecked_copy_reject_invalid_values(
    point_type: type, field: str, value: object
) -> None:
    panel = point_type is CrossSectionalForwardEquityPoint
    benchmark = "benchmark" if panel else "buy_and_hold"
    payload = {"timestamp": _START, "strategy_equity": 1.0, f"{benchmark}_equity": 1.0}
    point = point_type.model_validate(payload)
    with pytest.raises(ValueError):
        point_type.model_validate(dict(payload, **{field: value}))
    with pytest.raises(ValueError):
        point_type.model_validate(point.model_copy(update={field: value}))


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_unchecked_copy_fails_on_position_attachment(score_type: type) -> None:
    score = score_type.model_validate(_score_payload(score_type is CrossSectionalForwardScore))
    unchecked = score.model_copy(update={"as_of": _START.replace(tzinfo=None)})
    with pytest.raises(ValueError, match="timezone-aware"):
        if score_type is ForwardScore:
            PaperPosition(
                symbol="A", strategy_name="sma", parameters={}, frozen_at=_START, score=unchecked
            )
        else:
            CrossSectionalPosition(
                strategy_name="xs_momentum",
                parameters={},
                universe_symbols=["A"],
                cost_rate=0.001,
                frozen_at=_START,
                score=unchecked,
            )


def test_forward_panel_evidence_is_defensive_and_immutable() -> None:
    evidence = [_evidence()]
    score = CrossSectionalForwardScore.model_validate(dict(_score_payload(True), evidence=evidence))
    evidence.clear()
    assert score.evidence is not None
    assert len(score.evidence) == 1
    with pytest.raises(AttributeError, match="immutable"):
        score.evidence.clear()


@pytest.mark.parametrize(
    "evidence", [[], [_evidence(), _evidence()], [_evidence(), _evidence("B", "b" * 40)]]
)
def test_forward_panel_evidence_rejects_empty_duplicate_or_mixed_revision(evidence: list) -> None:
    with pytest.raises(ValueError):
        CrossSectionalForwardScore.model_validate(dict(_score_payload(True), evidence=evidence))


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_legacy_empty_curve_and_absent_evidence_remain_supported(
    score_type: type,
) -> None:
    score = score_type.model_validate(
        dict(_score_payload(score_type is CrossSectionalForwardScore), forward_equity=[])
    )
    assert score.forward_bars == 1
    assert score.evidence is None
    assert score_type.model_validate_json(score.model_dump_json()) == score


@pytest.mark.parametrize("point_type", _POINT_TYPES)
@given(value=st.floats(min_value=1e-12, max_value=1e12, allow_nan=False, allow_infinity=False))
def test_forward_point_positive_equity_and_offset_instant_round_trip(
    point_type: type, value: float
) -> None:
    benchmark = "benchmark" if point_type is CrossSectionalForwardEquityPoint else "buy_and_hold"
    point = point_type.model_validate(
        {
            "timestamp": _START.astimezone(timezone(timedelta(hours=-7))),
            "strategy_equity": value,
            f"{benchmark}_equity": value,
        }
    )
    assert point.timestamp.tzinfo is UTC
    assert point_type.model_validate_json(point.model_dump_json()) == point


@pytest.mark.parametrize("trades", [-1, 2])
def test_single_name_forward_trades_reject_invalid_counts(trades: int) -> None:
    with pytest.raises(ValueError, match="forward_trades"):
        ForwardScore.model_validate(dict(_score_payload(False), forward_trades=trades))


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_rejects_unchecked_nested_point_copy(score_type: type) -> None:
    score = score_type.model_validate(_score_payload(score_type is CrossSectionalForwardScore))
    point = score.forward_equity[0].model_copy(update={"strategy_equity": float("nan")})
    with pytest.raises(ValueError, match="finite and positive"):
        score_type.model_validate(dict(score.model_dump(), forward_equity=[point]))


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_rejects_duplicate_curve_timestamp(score_type: type) -> None:
    payload = _score_payload(score_type is CrossSectionalForwardScore)
    curve = payload["forward_equity"]
    assert isinstance(curve, list)
    curve.append(dict(curve[0]))
    payload["forward_bars"] = 2
    with pytest.raises(ValueError, match="strictly increasing"):
        score_type.model_validate(payload)


@pytest.mark.parametrize("score_type", _SCORE_TYPES)
def test_forward_score_zero_bars_supports_legacy_unmeasured_state(score_type: type) -> None:
    panel = score_type is CrossSectionalForwardScore
    benchmark = "benchmark" if panel else "buy_and_hold"
    payload = dict(
        _score_payload(panel),
        forward_bars=0,
        forward_return=0.0,
        forward_sharpe=0.0,
        forward_equity=[],
        as_of=_START - timedelta(days=1),
    )
    payload.update(
        {f"{benchmark}_return": 0.0, f"{benchmark}_sharpe": 0.0, f"beats_{benchmark}": False}
    )
    score = score_type.model_validate(payload)
    assert score.forward_bars == 0
    assert score_type.model_validate_json(score.model_dump_json()) == score
