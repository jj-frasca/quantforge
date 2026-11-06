"""Retained-history reporting; synthetic fixtures are not alpha experiments."""

import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.models import DataQualityReport
from app.research.dataset import ResearchDatasetEvidence
from app.research.lab.paper import ForwardScore, PaperPosition


def _position(
    symbol: str = "AAA",
    *,
    closed: bool = False,
    bars: int | None = 30,
    strategy_return: float = 0.0,
    hold_return: float = 0.0,
    strategy_sharpe: float = 0.0,
    hold_sharpe: float = 0.0,
    trades: int = 0,
    verdict: bool | None = None,
    stored_beat: bool = False,
) -> PaperPosition:
    cutoff = datetime(2026, 10, 1, tzinfo=UTC)
    score = (
        None
        if bars is None
        else ForwardScore(
            forward_bars=bars,
            forward_return=strategy_return,
            buy_and_hold_return=hold_return,
            forward_sharpe=strategy_sharpe,
            buy_and_hold_sharpe=hold_sharpe,
            forward_trades=trades,
            beats_buy_and_hold=stored_beat,
            as_of=cutoff,
        )
    )
    return PaperPosition(
        symbol=symbol,
        strategy_name="sma",
        parameters={"fast": 10, "slow": 30},
        frozen_at=datetime(2026, 1, 1, tzinfo=UTC),
        score=score,
        status="closed" if closed else "open",
        closed_at=cutoff if closed else None,
        exit_reasons=["risk"] if closed else [],
        survives_universe_deflation=verdict,
    )


def _report(positions: list[PaperPosition]) -> dict:
    # Deliberately import inside the test so a missing implementation is an
    # observed test failure, not a collection error.
    from app.research.lab.paper_evidence import summarize_paper_evidence

    return summarize_paper_evidence(positions)


def test_retained_history_exposes_survivor_sign_reversal() -> None:
    positions = [
        _position("OPEN", strategy_return=0.1),
        _position("LOSS1", closed=True, strategy_return=-0.2),
        _position("LOSS2", closed=True, strategy_return=-0.3),
    ]
    before = [p.model_dump_json() for p in positions]
    report = _report(positions)
    assert report["populations"]["all"]["median_return_difference"] == -0.2
    assert report["populations"]["open"]["median_return_difference"] == 0.1
    assert report["populations"]["closed"]["n_positions"] == 2
    assert len(report["rows"]) == 3
    assert [p.model_dump_json() for p in positions] == before


def test_missing_zero_bar_and_zero_turnover_are_distinct() -> None:
    report = _report(
        [
            _position("MISSING", bars=None),
            _position("PLACEHOLDER", bars=0),
            _position("INHERITED", strategy_return=0.2),
            _position("ZERO", hold_return=-0.1, hold_sharpe=-1.0),
        ]
    )
    all_rows = report["populations"]["all"]
    assert all_rows["n_measured"] == 2
    assert all_rows["n_missing_score"] == 1
    assert all_rows["n_zero_bar"] == 1
    assert all_rows["n_zero_turnover"] == 2
    assert all_rows["n_positive_return_difference"] == 2
    assert all_rows["n_positive_sharpe_difference"] == 1
    assert all_rows["n_stored_sharpe_beat"] == 0
    assert all_rows["n_path_nonzero"] == 0
    assert all_rows["n_path_unknown"] == 2
    assert report["rows"][0]["return_difference"] is None
    assert report["rows"][1]["return_difference"] is None


def test_empty_population_remains_unmeasured() -> None:
    report = _report([])
    for summary in report["populations"].values():
        assert summary["median_return_difference"] is None
        assert summary["mean_sharpe_difference"] is None
        assert summary["n_positions"] == 0
    assert report["adr033_trigger_met"] is False


@pytest.mark.parametrize("bars,expected", [(125, False), (126, True)])
def test_original_cohort_maturity_trigger_is_unchanged(bars: int, expected: bool) -> None:
    positions = [
        _position(f"{verdict}{i}", verdict=verdict, bars=bars)
        for verdict in (True, False)
        for i in range(20)
    ]
    report = _report(positions)
    assert report["adr033_trigger_met"] is expected
    assert report["cohorts"]["unknown"]["n_positions"] == 0


def test_nineteen_mature_survivors_and_unknowns_do_not_satisfy_trigger() -> None:
    positions = [_position(f"S{i}", verdict=True, bars=126) for i in range(19)]
    positions += [_position(f"N{i}", verdict=False, bars=126) for i in range(20)]
    positions += [_position("UNKNOWN", bars=126)]
    report = _report(positions)
    assert report["adr033_trigger_met"] is False
    assert report["cohorts"]["unknown"]["n_mature"] == 1


@pytest.mark.parametrize("intermediate,expected", [(1.0, False), (1.1, True)])
def test_path_evidence_includes_first_bar_and_round_trip(
    intermediate: float, expected: bool
) -> None:
    payload = _position(bars=2).model_dump()
    payload["score"]["forward_equity"] = [
        {
            "timestamp": datetime(2026, 9, 30, tzinfo=UTC),
            "strategy_equity": intermediate,
            "buy_and_hold_equity": 1.0,
        },
        {
            "timestamp": datetime(2026, 10, 1, tzinfo=UTC),
            "strategy_equity": 1.0,
            "buy_and_hold_equity": 1.0,
        },
    ]
    report = _report([PaperPosition.model_validate(payload)])
    assert report["rows"][0]["path_nonzero"] is expected
    assert report["populations"]["all"]["n_curve"] == 1
    assert report["populations"]["all"]["n_path_unknown"] == 0
    assert report["populations"]["all"]["n_zero_turnover"] == 1


def test_cli_reads_one_snapshot_and_preserves_its_bytes(tmp_path: Path) -> None:
    path = tmp_path / "snapshot.json"
    raw = json.dumps([_position().model_dump(mode="json")]).encode()
    path.write_bytes(raw)
    result = subprocess.run(
        [sys.executable, "-m", "scripts.paper_evidence_report", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(result.stdout)
    assert report["input_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["populations"]["all"]["n_positions"] == 1
    assert path.read_bytes() == raw
    assert list(tmp_path.iterdir()) == [path]


def test_report_revalidates_unchecked_inconsistent_score() -> None:
    position = _position()
    assert position.score is not None
    invalid = position.model_copy(
        update={"score": position.score.model_copy(update={"forward_return": float("nan")})}
    )
    with pytest.raises(ValueError):
        _report([invalid])


def test_lineage_availability_preserves_legacy_missingness() -> None:
    payload = _position().model_dump()
    payload["score"]["evidence"] = ResearchDatasetEvidence(
        quality_report=DataQualityReport(
            symbol="AAA", source="yfinance", checked_at=datetime(2026, 10, 1, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="synthetic",
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2027, 1, 1, tzinfo=UTC),
        git_commit_hash="a" * 40,
    )
    report = _report([PaperPosition.model_validate(payload), _position("LEGACY")])
    assert report["populations"]["all"]["n_lineage"] == 1
    assert report["rows"][0]["lineage_available"] is True
    assert report["rows"][1]["lineage_available"] is False


@given(
    strategy=st.floats(min_value=-0.9, max_value=2, allow_nan=False),
    hold=st.floats(min_value=-0.9, max_value=2, allow_nan=False),
)
def test_paired_return_difference_preserves_sign_and_comparator(
    strategy: float, hold: float
) -> None:
    report = _report([_position(strategy_return=strategy, hold_return=hold)])
    value = report["rows"][0]["return_difference"]
    assert value == strategy - hold
    assert (value > 0) == (strategy > hold)
    assert report["populations"]["all"]["median_return_difference"] == value
