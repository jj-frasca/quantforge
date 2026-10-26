"""ADR-379: invalid snapshot evidence cannot become absent fundamentals."""

import importlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import FundamentalSnapshot, parse_company_facts
from app.data.models import DataQualityReport
from app.research.dataset import ResearchDataset
from app.research.lab.experiment import (
    Experiment,
    InMemoryExperimentStore,
    JsonFileExperimentStore,
    PartitionedExperimentStore,
)
from app.research.lab.gate import GateConfig
from app.research.lab.universe import run_universe_hunt

FIELDS = ("revenue", "revenue_growth_yoy", "gross_margin", "net_margin", "eps", "pe_ratio")
SCRIPTS = ("shard_hunt", "run_hunt", "hunt")


def _payload() -> dict[str, object]:
    return {
        "symbol": "SYNTH",
        "cik": 1,
        "entity_name": "Synthetic",
        "fiscal_year": 2024,
        "form": "10-K",
        "accession_number": "synthetic",
        "source_url": "https://example.invalid",
        "revenue": 100.0,
        "revenue_growth_yoy": 0.1,
        "gross_margin": 0.2,
        "net_margin": 0.1,
        "eps": 1.0,
        "pe_ratio": 10.0,
    }


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), "nan", "inf", "-inf"])
@pytest.mark.parametrize("via_json", [False, True])
def test_snapshot_refuses_nonfinite_numeric_evidence(
    field: str, value: object, via_json: bool
) -> None:
    payload = {**_payload(), field: value}
    with pytest.raises(ValidationError, match=field):
        if via_json:
            FundamentalSnapshot.model_validate_json(json.dumps(payload))
        else:
            FundamentalSnapshot.model_validate(payload)


@pytest.mark.parametrize("field", FIELDS)
@settings(max_examples=30, deadline=None)
@given(value=st.floats(allow_nan=False, allow_infinity=False))
def test_finite_snapshot_values_round_trip_exactly(field: str, value: float) -> None:
    snapshot = FundamentalSnapshot.model_validate({**_payload(), field: value})
    restored = FundamentalSnapshot.model_validate_json(snapshot.model_dump_json())
    assert getattr(snapshot, field).hex() == value.hex()
    assert getattr(restored, field).hex() == value.hex()
    assert restored == snapshot


@pytest.mark.parametrize("field", FIELDS[1:])
def test_snapshot_keeps_nullable_metric_evidence(field: str) -> None:
    snapshot = FundamentalSnapshot.model_validate({**_payload(), field: None})
    assert getattr(snapshot, field) is None
    assert FundamentalSnapshot.model_validate_json(snapshot.model_dump_json()) == snapshot


def test_snapshot_keeps_finite_coercions_defaults_and_missing_optional_fields() -> None:
    payload = _payload()
    for field in FIELDS[1:]:
        del payload[field]
    snapshot = FundamentalSnapshot.model_validate({**payload, "revenue": "-0.25"})
    assert snapshot.revenue == -0.25
    assert snapshot.source == "SEC EDGAR"
    assert all(getattr(snapshot, field) is None for field in FIELDS[1:])


def _overflow_facts(current: float) -> dict[str, Any]:
    def fact(value: float, year: int) -> dict[str, object]:
        return {"val": value, "fy": year, "fp": "FY", "form": "10-K", "accn": "synthetic"}

    return {
        "cik": 1,
        "entityName": "Synthetic",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": [fact(1e-308, 2023), fact(current, 2024)]}},
                "NetIncomeLoss": {"units": {"USD": [fact(current, 2024)]}},
            }
        },
    }


class _CapturedMain(Exception):
    pass


def _capture_actual_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    script: str,
    fetch: Callable[[str], FundamentalSnapshot],
) -> Callable[[str], FundamentalSnapshot | None]:
    """Execute actual CLI wiring, stopping before the hunt and every network/store operation."""
    module = importlib.import_module(f"scripts.{script}")
    captured: list[Callable[[str], FundamentalSnapshot | None]] = []

    def blocked_history(*args: object, **kwargs: object) -> None:
        pytest.fail("history acquisition is outside this synthetic wrapper test")

    source = SimpleNamespace(fetch=fetch, fetch_history=blocked_history)
    monkeypatch.setattr(module, "SecEdgarFundamentalsSource", lambda **kwargs: source)
    monkeypatch.setattr(module, "current_git_revision", lambda: "a" * 40)
    for name in (
        "YFinanceAdapter",
        "PartitionedExperimentStore",
        "JsonFileExperimentStore",
        "PriorAwareExperimentStore",
    ):
        if hasattr(module, name):
            monkeypatch.setattr(module, name, lambda *args, **kwargs: object())
    if hasattr(module, "get_settings"):
        monkeypatch.setattr(module, "get_settings", lambda: object())
        monkeypatch.setattr(module, "build_data_adapter", lambda settings: object())
    if hasattr(module, "load_fundamentals_pool"):
        monkeypatch.setattr(module, "load_fundamentals_pool", lambda path: [])

    def capture(*args: object, **kwargs: Any) -> None:
        captured.append(kwargs["fundamentals_provider"])
        raise _CapturedMain

    monkeypatch.setattr(module, "run_universe_hunt", capture)
    universe = tmp_path / "universe.txt"
    universe.write_text("SYNTH\n")
    argv = (
        [script, "0", "1", str(universe), str(tmp_path / "scratch.json")]
        if script == "shard_hunt"
        else [script, "SYNTH"]
    )
    monkeypatch.setattr(module.sys, "argv", argv)
    with pytest.raises(_CapturedMain):
        module.main()
    assert len(captured) == 1
    return captured[0]


@pytest.mark.parametrize("script", SCRIPTS)
def test_actual_hunt_wrapper_propagates_existing_snapshot_validation_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str
) -> None:
    with pytest.raises(ValidationError) as original:
        FundamentalSnapshot.model_validate({**_payload(), "cik": "not an integer"})

    def fetch(symbol: str) -> FundamentalSnapshot:
        raise original.value

    provider = _capture_actual_provider(monkeypatch, tmp_path, script, fetch)
    with pytest.raises(ValidationError) as caught:
        provider("SYNTH")
    assert caught.value is original.value


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("current", [1e308, -1e308])
def test_actual_hunt_wrapper_propagates_finite_input_parser_overflow(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str, current: float
) -> None:
    provider = _capture_actual_provider(
        monkeypatch,
        tmp_path,
        script,
        lambda symbol: parse_company_facts(_overflow_facts(current), symbol),
    )
    with pytest.raises(ValidationError, match="revenue_growth_yoy"):
        provider("SYNTH")


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("error_type", [ValueError, OSError])
def test_actual_hunt_wrapper_preserves_nonvalidation_availability_fallback(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str, error_type: type[Exception]
) -> None:
    def fetch(symbol: str) -> FundamentalSnapshot:
        raise error_type("synthetic unavailable fundamentals")

    provider = _capture_actual_provider(monkeypatch, tmp_path, script, fetch)
    assert provider("SYNTH") is None


@pytest.mark.parametrize("script", SCRIPTS)
def test_actual_hunt_wrapper_preserves_finite_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str
) -> None:
    snapshot = FundamentalSnapshot.model_validate(_payload())
    provider = _capture_actual_provider(monkeypatch, tmp_path, script, lambda symbol: snapshot)
    assert provider("SYNTH") is snapshot


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("current", [1e308, -1e308])
def test_invalid_wrapper_snapshot_becomes_universe_error_before_search(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, script: str, current: float
) -> None:
    provider = _capture_actual_provider(
        monkeypatch,
        tmp_path,
        script,
        lambda symbol: parse_company_facts(_overflow_facts(current), symbol),
    )
    frame = pd.DataFrame(
        {"close": [100.0, 101.0, 100.0, 101.0]},
        index=pd.date_range("2024-01-01", periods=4, tz="UTC"),
    )
    dataset = ResearchDataset(
        frame=frame,
        quality_report=DataQualityReport(
            symbol="SYNTH", source="yfinance", checked_at=datetime(2026, 1, 1, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="synthetic",
        start=frame.index[0].to_pydatetime(),
        end=datetime(2024, 1, 5, tzinfo=UTC),
        git_commit_hash="a" * 40,
    )
    searches: list[bool] = []

    def forbidden_search(*args: object, **kwargs: object) -> None:
        searches.append(True)
        raise ValueError("search must not be invoked for invalid snapshots")

    monkeypatch.setattr("app.research.lab.universe.run_search", forbidden_search)
    store = InMemoryExperimentStore()
    result = run_universe_hunt(
        ["SYNTH"], ["sma"], lambda symbol: dataset, fundamentals_provider=provider, store=store
    )
    assert searches == []
    assert result.experiments == []
    assert result.filtered == {}
    assert set(result.errors) == {"SYNTH"}
    assert result.errors["SYNTH"].startswith("ValidationError:")
    assert store.all() == []


def _experiment() -> Experiment:
    return Experiment(
        symbol="SYNTH",
        strategy_names=[],
        trials=[],
        lifetime_trials=0,
        gate_config=GateConfig(),
        fundamentals=FundamentalSnapshot.model_validate(_payload()),
    )


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("via_json", [False, True])
def test_experiment_reconstruction_refuses_unchecked_nonfinite_snapshot(
    field: str, via_json: bool
) -> None:
    valid = _experiment()
    assert valid.fundamentals is not None
    bad = valid.model_copy(
        update={"fundamentals": valid.fundamentals.model_copy(update={field: float("nan")})}
    )
    payload = bad.model_dump(mode="json") if via_json else bad.model_dump(round_trip=True)
    with pytest.raises(ValidationError, match=field):
        if via_json:
            Experiment.model_validate_json(json.dumps(payload))
        else:
            Experiment.model_validate(payload)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("kind", ["memory", "json", "partitioned"])
def test_store_rejects_unchecked_nonfinite_snapshot_before_mutation(
    tmp_path: Path, kind: str, field: str
) -> None:
    store = (
        InMemoryExperimentStore()
        if kind == "memory"
        else JsonFileExperimentStore(tmp_path / "pool.json")
        if kind == "json"
        else PartitionedExperimentStore(tmp_path / "pool")
    )
    valid = _experiment()
    store.add(valid)
    before = {
        str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert valid.fundamentals is not None
    bad = valid.model_copy(
        update={"fundamentals": valid.fundamentals.model_copy(update={field: float("inf")})}
    )
    with pytest.raises(ValidationError, match=field):
        store.add(bad)
    after = {
        str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()
    }
    assert before == after
    assert [e.experiment_id for e in store.all()] == [valid.experiment_id]
