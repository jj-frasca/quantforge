"""Deep immutability and internal identity of paper-position claims (ADR-148)."""

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.data.models import DataQualityIssue, DataQualityReport
from app.research.dataset import ResearchDatasetEvidence
from app.research.lab.paper import (
    ForwardEquityPoint,
    ForwardScore,
    JsonFilePaperPortfolio,
    PaperPosition,
)

_FREEZE = datetime(2026, 1, 1, tzinfo=UTC)


def _evidence(symbol: str = "AAA") -> ResearchDatasetEvidence:
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
        git_commit_hash="a" * 40,
    )


def _score(*, evidence_symbol: str = "AAA") -> ForwardScore:
    return ForwardScore(
        forward_bars=2,
        forward_return=0.21,
        forward_sharpe=1.0,
        buy_and_hold_return=0.1025,
        buy_and_hold_sharpe=0.5,
        beats_buy_and_hold=True,
        as_of=datetime(2026, 1, 3, tzinfo=UTC),
        forward_equity=[
            ForwardEquityPoint(
                timestamp=datetime(2026, 1, 2, tzinfo=UTC),
                strategy_equity=1.1,
                buy_and_hold_equity=1.05,
            ),
            ForwardEquityPoint(
                timestamp=datetime(2026, 1, 3, tzinfo=UTC),
                strategy_equity=1.21,
                buy_and_hold_equity=1.1025,
            ),
        ],
        forward_trades=1,
        evidence=_evidence(evidence_symbol),
    )


def _position(**updates: object) -> PaperPosition:
    payload: dict[str, object] = {
        "symbol": "AAA",
        "strategy_name": "sma",
        "parameters": {"fast": 10, "slow": 30},
        "frozen_at": _FREEZE,
        "score": _score(),
        "status": "closed",
        "closed_at": datetime(2026, 1, 4, tzinfo=UTC),
        "exit_reasons": ["edge decayed"],
    }
    payload.update(updates)
    return PaperPosition.model_validate(payload)


def test_paper_position_claim_graph_is_defensive_immutable_and_round_trips() -> None:
    parameters = {"fast": 10, "slow": 30}
    reasons = ["edge decayed"]
    score = _score()
    position = _position(parameters=parameters, exit_reasons=reasons, score=score)
    before = position.model_dump(mode="json")

    parameters["fast"] = 999
    reasons.append("caller mutation")
    score.forward_equity.append(score.forward_equity[0])
    assert score.evidence is not None
    with pytest.raises(TypeError, match="immutable"):
        score.evidence.quality_report.issues[0].context["observed"] = [  # type: ignore[index]
            999.0
        ]
    assert position.model_dump(mode="json") == before

    with pytest.raises(TypeError, match="immutable"):
        position.parameters["fast"] = 999
    with pytest.raises(AttributeError, match="immutable"):
        position.exit_reasons.append("public mutation")
    assert position.score is not None
    with pytest.raises(AttributeError, match="immutable"):
        position.score.forward_equity.append(position.score.forward_equity[0])
    assert position.score.evidence is not None
    context = position.score.evidence.quality_report.issues[0].context
    assert context is not None
    with pytest.raises(TypeError, match="immutable"):
        context["observed"] = [999.0]

    restored = PaperPosition.model_validate_json(position.model_dump_json())
    assert restored == position
    assert restored.model_dump(mode="json") == before


@pytest.mark.parametrize(
    "updates, message",
    [
        ({"status": "open"}, "open position cannot have close metadata"),
        ({"status": "open", "closed_at": None}, "open position cannot have close metadata"),
        ({"status": "closed", "closed_at": None}, "closed position requires closed_at"),
        ({"status": "closed", "exit_reasons": []}, "closed position requires exit reasons"),
    ],
)
def test_paper_position_rejects_lifecycle_identity_drift(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _position(**updates)


def test_paper_position_rejects_score_evidence_for_another_symbol() -> None:
    with pytest.raises(ValidationError, match="score evidence symbol must match"):
        _position(score=_score(evidence_symbol="BBB"))


@pytest.mark.parametrize(
    "field, value, message",
    [
        ("forward_bars", -1, "forward_bars must be non-negative"),
        ("forward_trades", -1, "forward_trades must be non-negative"),
        ("forward_trades", 3, "forward_trades cannot exceed forward_bars"),
        ("forward_return", float("nan"), "forward statistics must be finite"),
        ("forward_sharpe", float("inf"), "forward statistics must be finite"),
    ],
)
def test_paper_position_rejects_invalid_score_scalars(
    field: str, value: object, message: str
) -> None:
    payload = _score().model_dump()
    payload[field] = value
    with pytest.raises(ValidationError, match=message):
        _position(score=ForwardScore.model_validate(payload))


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
def test_paper_position_rejects_invalid_nonempty_curve(mutation: str, message: str) -> None:
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
        curve[-1]["strategy_equity"] = 9.0

    with pytest.raises(ValidationError, match=message):
        _position(score=ForwardScore.model_validate(deepcopy(payload)))


def test_paper_portfolio_revalidates_claim_before_write(tmp_path: Path) -> None:
    path = tmp_path / "paper.json"
    store = JsonFilePaperPortfolio(path)
    position = _position()
    store.save([position])
    before = path.read_bytes()

    unchecked = position.model_copy(update={"status": "open"})
    with pytest.raises(ValidationError, match="open position cannot have close metadata"):
        store.save([unchecked])

    assert path.read_bytes() == before
