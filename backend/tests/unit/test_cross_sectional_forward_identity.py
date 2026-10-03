"""Deep immutability and internal identity of cross-sectional forward claims (ADR-149)."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.models import DataQualityIssue, DataQualityReport
from app.research.cross_sectional.forward import (
    CrossSectionalForwardEquityPoint,
    CrossSectionalForwardScore,
    CrossSectionalPosition,
)
from app.research.cross_sectional.forward_store import JsonFileCrossSectionalBook
from app.research.dataset import ResearchDatasetEvidence

_FREEZE = datetime(2026, 1, 1, tzinfo=UTC)


def _evidence(symbol: str, revision: str = "a" * 40) -> ResearchDatasetEvidence:
    return ResearchDatasetEvidence(
        quality_report=DataQualityReport(
            symbol=symbol,
            source="yfinance",
            checked_at=datetime(2026, 1, 3, tzinfo=UTC),
            issues=[
                DataQualityIssue(
                    check="price_anomaly",
                    severity="warning",
                    message="flags potential price anomaly",
                    context={"observed": [0.2]},
                )
            ],
        ),
        source="yfinance",
        adapter_version="test-v1",
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2026, 1, 4, tzinfo=UTC),
        git_commit_hash=revision,
    )


def _score(*, evidence: list[ResearchDatasetEvidence] | None = None) -> CrossSectionalForwardScore:
    return CrossSectionalForwardScore(
        forward_bars=2,
        forward_return=0.21,
        forward_sharpe=1.0,
        benchmark_return=0.1025,
        benchmark_sharpe=0.5,
        beats_benchmark=True,
        as_of=datetime(2026, 1, 3, tzinfo=UTC),
        forward_equity=[
            CrossSectionalForwardEquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                strategy_equity=1.1,
                benchmark_equity=1.05,
            ),
            CrossSectionalForwardEquityPoint(
                timestamp=datetime(2026, 1, 3, tzinfo=UTC),
                strategy_equity=1.21,
                benchmark_equity=1.1025,
            ),
        ],
        evidence=evidence or [_evidence("A"), _evidence("B")],
    )


def _position(**updates: object) -> CrossSectionalPosition:
    payload: dict[str, object] = {
        "strategy_name": "xs_momentum",
        "parameters": {"lookback": 10, "quantile": 0.2},
        "universe_symbols": ["A", "B"],
        "cost_rate": 0.001,
        "frozen_at": _FREEZE,
        "score": _score(),
        "status": "retired",
        "retired_at": datetime(2026, 1, 4, tzinfo=UTC),
        "exit_reasons": ["edge decayed"],
    }
    payload.update(updates)
    return CrossSectionalPosition.model_validate(payload)


def test_cross_sectional_forward_claim_is_defensive_immutable_and_round_trips() -> None:
    reasons = ["edge decayed"]
    score = _score()
    position = _position(exit_reasons=reasons, score=score)
    before = position.model_dump(mode="json")

    reasons.append("caller mutation")
    score.forward_equity.append(score.forward_equity[0])
    assert score.evidence is not None
    with pytest.raises(TypeError, match="immutable"):
        score.evidence[0].quality_report.issues[0].context["observed"] = [  # type: ignore[index]
            999.0
        ]
    assert position.model_dump(mode="json") == before

    with pytest.raises(AttributeError, match="immutable"):
        position.exit_reasons.append("public mutation")
    assert position.score is not None
    with pytest.raises(AttributeError, match="immutable"):
        position.score.forward_equity.append(position.score.forward_equity[0])
    assert position.score.evidence is not None
    with pytest.raises(AttributeError, match="immutable"):
        position.score.evidence.append(_evidence("C"))
    context = position.score.evidence[0].quality_report.issues[0].context
    assert context is not None
    with pytest.raises(TypeError, match="immutable"):
        context["observed"] = [999.0]

    restored = CrossSectionalPosition.model_validate_json(position.model_dump_json())
    assert restored == position
    assert restored.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"status": "open"}, "open factor cannot have retirement metadata"),
        ({"status": "open", "retired_at": None}, "open factor cannot have retirement metadata"),
        ({"status": "retired", "retired_at": None}, "retired factor requires retired_at"),
        ({"status": "retired", "exit_reasons": []}, "retired factor requires exit reasons"),
    ],
)
def test_cross_sectional_position_rejects_lifecycle_identity_drift(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _position(**updates)


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"cost_rate": -0.001}, "cost_rate must be finite and non-negative"),
        ({"cost_rate": float("nan")}, "cost_rate must be finite and non-negative"),
        ({"universe_symbols": []}, "frozen universe must be non-empty"),
        ({"universe_symbols": ["A", "A"]}, "frozen universe symbols must be unique"),
    ],
)
def test_cross_sectional_position_rejects_invalid_reconstruction_identity(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _position(**updates)


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("forward_bars", -1, "forward_bars must be non-negative"),
        ("forward_return", float("nan"), "forward statistics must be finite"),
        ("benchmark_sharpe", float("inf"), "forward statistics must be finite"),
    ],
)
def test_cross_sectional_position_rejects_invalid_score_scalars(
    field: str, value: object, message: str
) -> None:
    payload = _score().model_dump()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        _position(score=CrossSectionalForwardScore.model_validate(payload))


@pytest.mark.parametrize(
    "evidence, message",
    [
        ([_evidence("A")], "score evidence symbols must match frozen universe order"),
        (
            [_evidence("B"), _evidence("A")],
            "score evidence symbols must match frozen universe order",
        ),
        (
            [_evidence("A"), _evidence("B", revision="b" * 40)],
            "score evidence must name one git revision",
        ),
    ],
)
def test_cross_sectional_position_rejects_invalid_evidence_identity(
    evidence: list[ResearchDatasetEvidence], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _position(score=_score(evidence=evidence))


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("length", "forward equity length must match forward_bars"),
        ("order", "forward equity timestamps must be strictly increasing"),
        ("prefreeze", "forward equity timestamps must follow frozen_at"),
        ("nonpositive", "forward equity values must be finite and positive"),
        ("terminal", "forward equity terminal values must match score returns"),
    ],
)
def test_cross_sectional_position_rejects_invalid_nonempty_curve(
    mutation: str, message: str
) -> None:
    payload = _score().model_dump(mode="json")
    curve = payload["forward_equity"]
    assert isinstance(curve, list)
    if mutation == "length":
        curve.pop()
    elif mutation == "order":
        curve.reverse()
    elif mutation == "prefreeze":
        curve[0]["timestamp"] = _FREEZE.isoformat()
    elif mutation == "nonpositive":
        curve[0]["strategy_equity"] = 0.0
    else:
        curve[-1]["benchmark_equity"] = 9.0

    with pytest.raises(ValidationError, match=message):
        _position(score=CrossSectionalForwardScore.model_validate(deepcopy(payload)))


def test_cross_sectional_book_revalidates_claim_before_write(tmp_path: Path) -> None:
    path = tmp_path / "forward.json"
    store = JsonFileCrossSectionalBook(path)
    position = _position()
    store.save([position])
    before = path.read_bytes()

    unchecked = position.model_copy(update={"status": "open"})
    with pytest.raises(ValidationError, match="open factor cannot have retirement metadata"):
        store.save([unchecked])

    assert path.read_bytes() == before
