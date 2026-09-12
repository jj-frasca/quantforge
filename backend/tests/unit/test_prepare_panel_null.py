"""Production preparation entry point for the frozen ADR-081 panel-null inputs."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest
from scripts import prepare_panel_null as prepare_module
from scripts.prepare_panel_null import (
    DATA_ROOT,
    parse_utc_instant,
    prepare_panel_null_source_files,
)

from app.data.models import PriceBar
from app.data.sources.retry import CLOUD, RetryPolicy
from app.research.lab.experiment import Experiment, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.panel_null import (
    PanelNullCohort,
    PanelSymbolExcess,
    SelectedPanelNullCohort,
    bind_panel_null_cohort,
    load_panel_null_cohort,
    load_prepared_panel_null_source,
    prepare_panel_null_source,
)


def _selected() -> SelectedPanelNullCohort:
    return SelectedPanelNullCohort(
        symbols=("AAA", "BBB"),
        symbol_excesses=(
            PanelSymbolExcess(symbol="AAA", walk_forward=-0.2, purged_cv=0.1),
            PanelSymbolExcess(symbol="BBB", walk_forward=0.0, purged_cv=0.2),
        ),
        target_n_bars=4,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=GateConfig().version_hash,
        min_symbols=2,
    )


def _bars(symbol: str) -> list[PriceBar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        PriceBar(
            symbol=symbol,
            timestamp_utc=start + timedelta(days=offset),
            open=Decimal(100 + offset),
            high=Decimal(102 + offset),
            low=Decimal(99 + offset),
            close=Decimal(101 + offset),
            volume=1_000 + offset,
            adj_factor=Decimal("1"),
            source="yfinance",
        )
        for offset in range(6)
    ]


def _observed_search(frame: pd.DataFrame, symbol: str) -> Experiment:
    assert len(frame) == 4
    walk_forward = 0.7 if symbol == "AAA" else 0.5
    trial = Trial(
        strategy_name="selected",
        parameters={},
        observed_sharpe=0.0,
        deflated_sharpe=0.0,
        pbo=0.1,
        parameter_stability_score=0.8,
        walk_forward_oos_sharpe=walk_forward,
        purged_cv_oos_sharpe=None,
    )
    return Experiment(
        symbol=symbol,
        strategy_names=["selected"],
        gate_config=GateConfig(),
        trials=[trial],
        lifetime_trials=1,
        best_strategy_name="selected",
        selected_trial_index=0,
        search_config_version="search-v1",
        n_bars=4,
        walk_forward_hold_sharpe=0.2,
    )


def test_parse_utc_instant_requires_an_explicit_utc_offset() -> None:
    expected = datetime(2026, 9, 10, 20, 0, tzinfo=UTC)

    assert parse_utc_instant("2026-09-10T20:00:00Z") == expected
    assert parse_utc_instant("2026-09-10T20:00:00+00:00") == expected
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        parse_utc_instant("2026-09-10T20:00:00")
    with pytest.raises(ValueError, match="timezone-aware UTC"):
        parse_utc_instant("2026-09-10T13:00:00-07:00")


def test_preparation_reuses_one_cutoff_and_cloud_retry_then_writes_immutable_inputs(
    tmp_path: Path,
) -> None:
    selected = _selected()
    asof = datetime(2026, 1, 6, 12, tzinfo=UTC)
    calls: list[tuple[str, datetime, datetime]] = []
    policies: list[RetryPolicy] = []

    class FakeAdapter:
        def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
            calls.append((symbol, start, end))
            return _bars(symbol)

    def adapter_factory(*, retry: RetryPolicy) -> FakeAdapter:
        policies.append(retry)
        return FakeAdapter()

    source_path = tmp_path / "source.npz"
    manifest_path = tmp_path / "cohort.json"
    prepare_panel_null_source_files(
        selected,
        asof=asof,
        source_path=source_path,
        manifest_path=manifest_path,
        base_seed=17,
        code_revision="1" * 40,
        adapter_factory=adapter_factory,
        search=_observed_search,
    )

    assert policies == [CLOUD]
    assert [symbol for symbol, _, _ in calls] == ["AAA", "BBB"]
    assert {end for _, _, end in calls} == {asof}
    prepared = load_prepared_panel_null_source(source_path)
    cohort = load_panel_null_cohort(manifest_path)
    assert prepared.source_end.isoformat() == "2026-01-05"
    assert cohort.source_sha256 == prepared.source_sha256
    assert cohort.base_seed == 17
    assert cohort.generator_version == "joint-iid-calendar-v1"
    assert cohort.diagnostic_version == "equal-symbol-source-matched-excess-v2"
    assert [value.walk_forward for value in cohort.symbol_excesses] == pytest.approx([0.5, 0.3])

    with pytest.raises(FileExistsError):
        prepare_panel_null_source_files(
            selected,
            asof=asof,
            source_path=source_path,
            manifest_path=tmp_path / "other.json",
            base_seed=17,
            code_revision="1" * 40,
            adapter_factory=adapter_factory,
            search=_observed_search,
        )
    assert len(calls) == 2, "existing outputs must fail before any vendor call"


def test_preparation_refuses_generated_data_paths_before_fetching() -> None:
    called = False

    class UnusedAdapter:
        def fetch_price_bars(self, symbol: str, start: datetime, end: datetime) -> list[PriceBar]:
            raise AssertionError((symbol, start, end))

    def adapter_factory(*, retry: RetryPolicy) -> UnusedAdapter:
        del retry
        nonlocal called
        called = True
        return UnusedAdapter()

    with pytest.raises(ValueError, match="scratch-only"):
        prepare_panel_null_source_files(
            _selected(),
            asof=datetime(2026, 1, 6, 12, tzinfo=UTC),
            source_path=DATA_ROOT / "panel_null_calibration" / "source.npz",
            manifest_path=DATA_ROOT / "panel_null_calibration" / "cohort.json",
            base_seed=17,
            code_revision="1" * 40,
            adapter_factory=adapter_factory,
        )
    assert not called


def test_cli_freezes_current_identity_and_forwards_the_explicit_cutoff(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    selected = _selected()
    captured: dict[str, object] = {}

    class FakeStore:
        def __init__(self, path: Path) -> None:
            captured["pool"] = path

        def all(self) -> list[object]:
            return [object()]

    def select(experiments: object, **kwargs: object) -> SelectedPanelNullCohort:
        captured["experiments"] = experiments
        captured["selection"] = kwargs
        return selected

    def prepare(selected_arg: SelectedPanelNullCohort, **kwargs: object) -> PanelNullCohort:
        captured["selected"] = selected_arg
        captured["preparation"] = kwargs
        prepared = prepare_panel_null_source(
            {
                symbol: prepare_module.bars_to_frame(_bars(symbol)[:4])
                for symbol in selected_arg.symbols
            },
            selected_arg.symbols,
            target_n_bars=4,
        )
        return bind_panel_null_cohort(
            selected_arg,
            prepared,
            generator_version="joint-iid-calendar-v1",
            diagnostic_version="equal-symbol-excess-v1",
            base_seed=17,
            code_revision="1" * 40,
        )

    monkeypatch.setattr(prepare_module, "PartitionedExperimentStore", FakeStore)
    monkeypatch.setattr(prepare_module, "select_panel_null_cohort", select)
    monkeypatch.setattr(prepare_module, "prepare_panel_null_source_files", prepare)
    pool = tmp_path / "pool"

    prepare_module.main(
        [
            "2026-09-10T20:00:00Z",
            str(tmp_path / "source.npz"),
            str(tmp_path / "cohort.json"),
            "--base-seed",
            "17",
            "--code-revision",
            "1" * 40,
            "--pool-dir",
            str(pool),
            "--target-n-bars",
            "4",
        ]
    )

    assert captured["pool"] == pool
    selection = captured["selection"]
    assert isinstance(selection, dict)
    assert selection["target_n_bars"] == 4
    assert selection["history_tolerance"] == 0.10
    assert selection["min_symbols"] == 30
    assert selection["search_config_version"] != "legacy-unspecified"
    preparation = captured["preparation"]
    assert isinstance(preparation, dict)
    assert preparation["asof"] == datetime(2026, 9, 10, 20, 0, tzinfo=UTC)
    assert preparation["base_seed"] == 17
    assert preparation["code_revision"] == "1" * 40
