"""ADR-374: valuation identity refusal belongs to the per-symbol hunt boundary."""

from datetime import UTC, datetime
from unittest.mock import Mock
from uuid import UUID

import pandas as pd
import pytest

from app.data.models import DataQualityReport
from app.research.dataset import ResearchDataset
from app.research.lab import universe
from app.research.lab.experiment import Experiment, InMemoryExperimentStore, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.value_filter import ValueGateConfig
from app.research.valuation import UndervaluationScore

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _score(symbol: str, score: float | None = 0.9) -> UndervaluationScore:
    return UndervaluationScore(
        symbol=symbol,
        cik=1,
        entity_name="Synthetic",
        fiscal_year=2025,
        form="10-K",
        accession_number="synthetic",
        source_url="synthetic",
        current_price=12.0,
        pe_ratio=None,
        pe_percentile=None,
        ps_ratio=None,
        ps_percentile=None,
        intrinsic_value_per_share=24.0,
        margin_of_safety=0.5,
        growth_rate_used=None,
        fcf_is_net_income_proxy=False,
        score=score,
        flags=[],
    )


def _experiment(_frame: pd.DataFrame, symbol: str, *_args: object, **_kwargs: object) -> Experiment:
    return Experiment(
        created_at=_NOW,
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={},
                observed_sharpe=0.1,
                deflated_sharpe=0.0,
                pbo=0.5,
                parameter_stability_score=0.5,
            )
        ],
        lifetime_trials=1,
        best_strategy_name="sma",
        selected_trial_index=0,
    )


def _dataset(symbol: str) -> ResearchDataset:
    return ResearchDataset(
        frame=pd.DataFrame(
            {"close": [10.0, 11.0, 12.0]},
            index=pd.date_range("2025-01-01", periods=3, tz="UTC"),
        ),
        quality_report=DataQualityReport(
            id=UUID(int=5), symbol=symbol, source="yfinance", checked_at=_NOW
        ),
        source="yfinance",
        adapter_version="synthetic",
        start=datetime(2025, 1, 1, tzinfo=UTC),
        end=datetime(2025, 1, 4, tzinfo=UTC),
        git_commit_hash="b" * 40,
    )


@pytest.mark.parametrize("screen_enabled", [False, True])
@pytest.mark.parametrize("earlier_good", [False, True])
def test_hunt_wrong_valuation_symbol_records_error_and_continues(
    monkeypatch: pytest.MonkeyPatch, screen_enabled: bool, earlier_good: bool
) -> None:
    search = Mock(side_effect=_experiment)
    monkeypatch.setattr(universe, "run_search", search)
    names = ["GOOD1", "BAD", "GOOD2"] if earlier_good else ["BAD", "GOOD2"]
    store = InMemoryExperimentStore()

    result = universe.run_universe_hunt(
        names,
        ["sma"],
        _dataset,
        value_provider=lambda symbol: _score("WRONG" if symbol == "BAD" else symbol),
        value_config=ValueGateConfig() if screen_enabled else None,
        store=store,
    )

    expected = [symbol for symbol in names if symbol != "BAD"]
    assert [row.symbol for row in result.experiments] == expected
    assert [row.symbol for row in store.all()] == expected
    assert set(result.errors) == {"BAD"}
    assert result.errors["BAD"].startswith("ValidationError:")
    assert "undervaluation_score symbol must match experiment" in result.errors["BAD"]
    assert result.filtered == {}
    # Refusal remains after search; no early identity shortcut or unattempted-search claim.
    assert [call.args[1] for call in search.call_args_list] == names
    for row in result.experiments:
        assert row.undervaluation_score == _score(row.symbol)
        assert row.manifest is not None and row.manifest.symbol == row.symbol


@pytest.mark.parametrize("screen_enabled", [False, True])
@pytest.mark.parametrize("kind", ["absent", "none", "unscorable", "valid"])
def test_hunt_valid_or_absent_valuation_retains_attachment(
    monkeypatch: pytest.MonkeyPatch, screen_enabled: bool, kind: str
) -> None:
    monkeypatch.setattr(universe, "run_search", _experiment)
    score = (
        None
        if kind in {"absent", "none"}
        else _score("GOOD", None if kind == "unscorable" else 0.9)
    )
    provider = None if kind == "absent" else lambda _symbol: score
    store = InMemoryExperimentStore()
    result = universe.run_universe_hunt(
        ["GOOD"],
        ["sma"],
        _dataset,
        value_provider=provider,
        value_config=ValueGateConfig() if screen_enabled else None,
        store=store,
    )
    assert result.errors == result.filtered == {}
    assert len(result.experiments) == len(store.all()) == 1
    assert result.experiments[0].undervaluation_score == score
    assert store.all()[0].model_dump_json() == result.experiments[0].model_dump_json()


def test_hunt_wrong_symbol_filtered_score_keeps_existing_admission_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    search = Mock(side_effect=AssertionError("filtered score must not reach search"))
    frames = Mock(side_effect=AssertionError("filtered score must not request a frame"))
    monkeypatch.setattr(universe, "run_search", search)
    result = universe.run_universe_hunt(
        ["BAD"],
        ["sma"],
        frames,
        value_provider=lambda _symbol: _score("WRONG", 0.1),
        value_config=ValueGateConfig(),
    )
    assert result.experiments == []
    assert result.errors == {}
    assert set(result.filtered) == {"BAD"}
    frames.assert_not_called()
    search.assert_not_called()


@pytest.mark.parametrize("exception_type", [ValueError, OSError])
def test_hunt_store_failure_still_propagates_after_valid_attachment(
    monkeypatch: pytest.MonkeyPatch, exception_type: type[Exception]
) -> None:
    monkeypatch.setattr(universe, "run_search", _experiment)
    store = InMemoryExperimentStore()
    failure = exception_type("synthetic store fault")
    add = Mock(side_effect=failure)
    monkeypatch.setattr(store, "add", add)
    with pytest.raises(exception_type, match="synthetic store fault") as caught:
        universe.run_universe_hunt(
            ["GOOD", "LATER"],
            ["sma"],
            _dataset,
            value_provider=_score,
            store=store,
        )
    assert caught.value is failure
    assert add.call_count == 1
    assert store.all() == []
