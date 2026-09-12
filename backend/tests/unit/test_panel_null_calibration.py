"""Whole-panel artifact identity, joint-row generation, and consolidation for ADR-081."""

import json
from dataclasses import replace
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.research.lab.calibration import calibration_search_version
from app.research.lab.experiment import Experiment, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.panel_null import (
    PanelDiagnosticInference,
    PanelNullCalibration,
    PanelNullCohort,
    PanelNullError,
    PanelNullReplicate,
    PanelNullShard,
    PanelSymbolExcess,
    SelectedPanelNullCohort,
    bind_panel_null_cohort,
    fetch_panel_null_source,
    infer_panel_null,
    joint_iid_panel_null,
    load_panel_null_cohort,
    load_panel_null_shard,
    load_prepared_panel_null_source,
    make_production_panel_null_search,
    measure_observed_panel_excesses,
    merge_panel_null_shards,
    panel_seed,
    prepare_panel_null_source,
    run_panel_null_batch,
    run_panel_null_replicate,
    run_production_panel_null_batch,
    save_panel_null_cohort,
    save_panel_null_shard,
    save_prepared_panel_null_source,
    select_panel_null_cohort,
)


def _cohort(
    *,
    source_digest: str = "a" * 64,
    n_replicates: int = 4,
    min_successful_symbols: int = 2,
) -> PanelNullCohort:
    return PanelNullCohort(
        symbols=("AAA", "BBB"),
        symbol_excesses=(
            PanelSymbolExcess(symbol="AAA", walk_forward=-0.2, purged_cv=0.1),
            PanelSymbolExcess(symbol="BBB", walk_forward=0.0, purged_cv=None),
        ),
        source_start=date(1995, 1, 3),
        source_end=date(2026, 8, 31),
        source_sha256=source_digest,
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version="gate-v1",
        code_revision="1" * 40,
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-excess-v1",
        base_seed=17,
        n_replicates=n_replicates,
        min_successful_symbols=min_successful_symbols,
    )


def test_panel_null_cohort_requires_an_exact_git_revision() -> None:
    cohort = _cohort()

    assert cohort.model_dump()["code_revision"] == "1" * 40
    for invalid in ("", "1" * 39, "1" * 41, "G" * 40, "A" * 40):
        with pytest.raises(ValidationError, match="code_revision"):
            PanelNullCohort.model_validate({**cohort.model_dump(), "code_revision": invalid})


def _replicate(index: int, *, successful_symbols: int = 2) -> PanelNullReplicate:
    return PanelNullReplicate(
        panel_index=index,
        panel_id=f"panel-{index:03d}",
        seed=panel_seed(17, index),
        successful_symbols=successful_symbols,
        errors=(),
        walk_forward_excess=-0.01 + index / 1000,
        purged_cv_excess=index / 2000,
    )


def _calibration_with_walk_forward(values: list[float]) -> PanelNullCalibration:
    cohort = _cohort(n_replicates=len(values))
    cohort = cohort.model_copy(
        update={
            "symbol_excesses": tuple(
                value.model_copy(update={"purged_cv": value.walk_forward})
                for value in cohort.symbol_excesses
            )
        }
    )
    replicates = tuple(
        _replicate(index).model_copy(update={"walk_forward_excess": value})
        for index, value in enumerate(values)
    )
    return PanelNullCalibration(cohort=cohort, replicates=replicates)


def test_panel_null_inference_uses_fixed_tail_counts_and_plus_one_p_value() -> None:
    calibration = _calibration_with_walk_forward([-1.0] * 3 + [1.0] * 397)

    result = infer_panel_null(calibration).walk_forward

    assert isinstance(result, PanelDiagnosticInference)
    assert result.real_statistic == pytest.approx(-0.1)
    assert result.null_median == pytest.approx(1.0)
    assert result.null_p025 == pytest.approx(1.0)
    assert result.null_p975 == pytest.approx(1.0)
    assert result.lower_tail_count == 3
    assert result.upper_tail_count == 397
    assert result.two_sided_p_value == pytest.approx(8 / 401)
    assert result.tail_interval_confidence == pytest.approx(0.975)
    assert result.simultaneous_confidence == pytest.approx(0.95)
    assert result.lower_tail_interval.low == pytest.approx(0.0011875146623632955)
    assert result.lower_tail_interval.high == pytest.approx(0.024143766938848475)
    assert result.resolution == "separated_below"


def test_panel_null_inference_keeps_four_tail_hits_unresolved() -> None:
    result = infer_panel_null(_calibration_with_walk_forward([-1.0] * 4 + [1.0] * 396)).walk_forward

    assert result.lower_tail_interval.high == pytest.approx(0.02794221048906605)
    assert result.resolution == "unresolved"


def test_panel_null_inference_resolves_the_fixed_upper_tail() -> None:
    result = infer_panel_null(_calibration_with_walk_forward([-1.0] * 397 + [1.0] * 3)).walk_forward

    assert result.upper_tail_count == 3
    assert result.upper_tail_interval.high < 0.025
    assert result.resolution == "separated_above"


def test_panel_null_inference_calls_both_well_inside_tails_not_separated() -> None:
    result = infer_panel_null(
        _calibration_with_walk_forward([-1.0] * 200 + [1.0] * 200)
    ).walk_forward

    assert result.lower_tail_interval.low > 0.025
    assert result.upper_tail_interval.low > 0.025
    assert result.two_sided_p_value == 1.0
    assert result.resolution == "not_separated"


def test_panel_null_inference_does_not_filter_partial_secondary_diagnostics() -> None:
    calibration = _calibration_with_walk_forward([-1.0, 1.0, -1.0, 1.0])
    assert infer_panel_null(calibration).purged_cv is not None

    incomplete = calibration.model_copy(
        update={
            "replicates": (
                *calibration.replicates[:-1],
                calibration.replicates[-1].model_copy(update={"purged_cv_excess": None}),
            )
        }
    )
    assert infer_panel_null(incomplete).purged_cv is None

    missing_real = calibration.model_copy(update={"cohort": _cohort(n_replicates=4)})
    assert infer_panel_null(missing_real).purged_cv is None


def _source_panel() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2020-01-02", periods=6, freq="B", tz="UTC")
    returns = {
        "AAA": np.array([0.0, 0.01, -0.02, 0.03, -0.01, 0.02]),
        "BBB": np.array([0.0, 0.02, -0.01, 0.04, -0.03, 0.01]),
    }
    panel: dict[str, pd.DataFrame] = {}
    for offset, (symbol, values) in enumerate(returns.items(), start=1):
        closes = 100.0 * np.cumprod(1.0 + values)
        panel[symbol] = pd.DataFrame(
            {
                "open": closes * (0.99 + offset / 1000),
                "high": closes * (1.01 + offset / 1000),
                "low": closes * (0.98 + offset / 1000),
                "close": closes,
                "volume": offset * 1000 + np.arange(len(index)),
            },
            index=index,
        )
    return panel


def _experiment(
    symbol: str,
    *,
    walk_forward: float | None,
    walk_forward_hold: float | None,
    purged_cv: float | None = None,
    purged_cv_hold: float | None = None,
    n_bars: int = 7400,
    search_version: str = "search-v1",
    gate_config: GateConfig | None = None,
    selected_trial_index: int | None = 0,
) -> Experiment:
    trials = [
        Trial(
            strategy_name="selected",
            parameters={},
            observed_sharpe=0.0,
            deflated_sharpe=-1.0,
            pbo=0.1,
            parameter_stability_score=0.8,
            walk_forward_oos_sharpe=walk_forward,
            purged_cv_oos_sharpe=purged_cv,
        ),
        Trial(
            strategy_name="max-dsr",
            parameters={},
            observed_sharpe=0.0,
            deflated_sharpe=2.0,
            pbo=0.1,
            parameter_stability_score=0.8,
            walk_forward_oos_sharpe=99.0,
            purged_cv_oos_sharpe=99.0,
        ),
    ]
    return Experiment(
        symbol=symbol,
        strategy_names=[trial.strategy_name for trial in trials],
        gate_config=gate_config or GateConfig(),
        trials=trials,
        lifetime_trials=2,
        best_strategy_name="selected" if selected_trial_index == 0 else None,
        selected_trial_index=selected_trial_index,
        search_config_version=search_version,
        n_bars=n_bars,
        walk_forward_hold_sharpe=walk_forward_hold,
        purged_cv_hold_sharpe=purged_cv_hold,
    )


def test_select_panel_null_cohort_matches_identity_and_weights_each_symbol_once() -> None:
    gate = GateConfig()
    experiments = [
        _experiment(
            "BBB",
            walk_forward=0.5,
            walk_forward_hold=0.2,
            purged_cv=0.6,
            purged_cv_hold=0.1,
            gate_config=gate,
        ),
        _experiment(
            "AAA",
            walk_forward=0.4,
            walk_forward_hold=0.2,
            purged_cv=0.3,
            purged_cv_hold=0.1,
            gate_config=gate,
        ),
        _experiment(
            "AAA",
            walk_forward=0.8,
            walk_forward_hold=0.2,
            purged_cv=None,
            purged_cv_hold=None,
            gate_config=gate,
        ),
        _experiment(
            "BELOW-TARGET-HISTORY",
            walk_forward=1.0,
            walk_forward_hold=0.0,
            n_bars=7000,
            gate_config=gate,
        ),
        _experiment(
            "WRONG-SEARCH",
            walk_forward=1.0,
            walk_forward_hold=0.0,
            search_version="search-v2",
            gate_config=gate,
        ),
        _experiment(
            "WRONG-GATE",
            walk_forward=1.0,
            walk_forward_hold=0.0,
            gate_config=GateConfig(trial_budget=199),
        ),
        _experiment(
            "UNMEASURED",
            walk_forward=None,
            walk_forward_hold=None,
            gate_config=gate,
        ),
    ]

    selected = select_panel_null_cohort(
        experiments,
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )

    assert selected.symbols == ("AAA", "BBB")
    assert selected.target_n_bars == 7400
    assert selected.history_tolerance == pytest.approx(0.10)
    assert selected.search_config_version == "search-v1"
    assert selected.gate_config_version == gate.version_hash
    assert [value.symbol for value in selected.symbol_excesses] == ["AAA", "BBB"]
    assert [value.walk_forward for value in selected.symbol_excesses] == pytest.approx([0.4, 0.3])
    assert [value.purged_cv for value in selected.symbol_excesses] == pytest.approx([0.2, 0.5])


def test_select_panel_null_cohort_uses_the_persisted_selected_trial() -> None:
    gate = GateConfig()

    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, gate_config=gate),
            _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, gate_config=gate),
        ],
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )

    assert [value.walk_forward for value in selected.symbol_excesses] == pytest.approx([0.2, 0.3])


def test_select_panel_null_cohort_fails_before_generation_below_symbol_floor() -> None:
    gate = GateConfig()

    with pytest.raises(ValueError, match=r"only 1 measured symbols.*requires 2"):
        select_panel_null_cohort(
            [_experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, gate_config=gate)],
            target_n_bars=7400,
            history_tolerance=0.10,
            search_config_version="search-v1",
            gate_config_version=gate.version_hash,
            min_symbols=2,
        )


def test_select_panel_null_cohort_rejects_duplicate_experiment_identity() -> None:
    gate = GateConfig()
    duplicated = _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, gate_config=gate)

    with pytest.raises(ValueError, match="duplicate experiment id"):
        select_panel_null_cohort(
            [
                duplicated,
                duplicated,
                _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, gate_config=gate),
            ],
            target_n_bars=7400,
            history_tolerance=0.10,
            search_config_version="search-v1",
            gate_config_version=gate.version_hash,
            min_symbols=2,
        )


def test_prepare_panel_null_source_freezes_order_calendar_and_digest() -> None:
    source = _source_panel()
    source["AAA"].iloc[1, source["AAA"].columns.get_loc("volume")] = np.nan
    source["BBB"].iloc[4, source["BBB"].columns.get_loc("close")] = np.nan

    prepared = prepare_panel_null_source(source, ("BBB", "AAA"), target_n_bars=3)

    assert prepared.symbols == ("BBB", "AAA")
    assert prepared.target_n_bars == 3
    assert prepared.source_start == date(2020, 1, 6)
    assert prepared.source_end == date(2020, 1, 9)
    assert len(prepared.source_sha256) == 64
    panel = prepared.to_frames()
    assert tuple(panel) == prepared.symbols
    assert panel["AAA"].index.equals(panel["BBB"].index)
    assert panel["AAA"].index.tolist() == [
        pd.Timestamp("2020-01-06", tz="UTC"),
        pd.Timestamp("2020-01-07", tz="UTC"),
        pd.Timestamp("2020-01-09", tz="UTC"),
    ]
    assert not any(frame.isna().any().any() for frame in panel.values())


def test_prepare_panel_null_source_digest_is_canonical_and_value_sensitive() -> None:
    source = _source_panel()
    reordered = {
        symbol: frame.loc[:, ["volume", "close", "low", "high", "open"]]
        for symbol, frame in reversed(tuple(source.items()))
    }

    first = prepare_panel_null_source(source, ("AAA", "BBB"), target_n_bars=5)
    second = prepare_panel_null_source(reordered, ("AAA", "BBB"), target_n_bars=5)
    assert second.source_sha256 == first.source_sha256

    changed = {symbol: frame.copy() for symbol, frame in source.items()}
    changed["AAA"].iloc[-1, changed["AAA"].columns.get_loc("volume")] += 1
    assert (
        prepare_panel_null_source(changed, ("AAA", "BBB"), target_n_bars=5).source_sha256
        != first.source_sha256
    )
    assert (
        prepare_panel_null_source(source, ("BBB", "AAA"), target_n_bars=5).source_sha256
        != first.source_sha256
    )


def test_prepare_panel_null_source_copies_the_frozen_source() -> None:
    source = _source_panel()
    prepared = prepare_panel_null_source(source, ("AAA", "BBB"), target_n_bars=5)
    digest = prepared.source_sha256

    source["AAA"].iloc[-1, source["AAA"].columns.get_loc("close")] = 1.0
    exported = prepared.to_frames()
    exported["AAA"].iloc[-1, exported["AAA"].columns.get_loc("close")] = 2.0

    assert prepared.source_sha256 == digest
    assert prepared.to_frames()["AAA"].iloc[-1]["close"] != 2.0


def test_prepared_panel_source_direct_construction_cannot_drift_from_its_frames() -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)

    with pytest.raises(ValueError, match="digest"):
        replace(prepared, source_sha256="a" * 64)
    with pytest.raises(ValueError, match="calendar range"):
        replace(prepared, source_start=date(1999, 1, 1))


def test_prepared_panel_null_source_archive_round_trips_losslessly(tmp_path: Path) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("BBB", "AAA"), target_n_bars=5)
    path = tmp_path / "prepared-panel.npz"

    save_prepared_panel_null_source(prepared, path)
    loaded = load_prepared_panel_null_source(path)

    assert loaded.symbols == prepared.symbols
    assert loaded.target_n_bars == prepared.target_n_bars
    assert loaded.source_start == prepared.source_start
    assert loaded.source_end == prepared.source_end
    assert loaded.source_sha256 == prepared.source_sha256
    for symbol in prepared.symbols:
        pd.testing.assert_frame_equal(loaded.to_frames()[symbol], prepared.to_frames()[symbol])
    with pytest.raises(FileExistsError):
        save_prepared_panel_null_source(prepared, path)


def test_prepared_panel_null_source_archive_rejects_tampering(tmp_path: Path) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    path = tmp_path / "prepared-panel.npz"
    save_prepared_panel_null_source(prepared, path)
    with np.load(path, allow_pickle=False) as archive:
        fields = {name: archive[name].copy() for name in archive.files}
    fields["ohlcv"][0, -1, 3] += 1.0
    np.savez_compressed(path, **fields)

    with pytest.raises(ValueError, match="digest"):
        load_prepared_panel_null_source(path)


def test_prepared_panel_null_source_archive_rejects_schema_drift(tmp_path: Path) -> None:
    path = tmp_path / "prepared-panel.npz"
    np.savez_compressed(path, format_version=np.array("wrong"))

    with pytest.raises(ValueError, match="fields"):
        load_prepared_panel_null_source(path)


def test_panel_null_cohort_manifest_is_exclusive_and_revalidates_identity(tmp_path: Path) -> None:
    cohort = _cohort()
    path = tmp_path / "panel-cohort.json"

    save_panel_null_cohort(cohort, path)

    assert load_panel_null_cohort(path) == cohort
    with pytest.raises(FileExistsError):
        save_panel_null_cohort(cohort, path)

    tampered = cohort.model_dump(mode="json")
    tampered["source_sha256"] = "not-a-digest"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValidationError, match="source_sha256"):
        load_panel_null_cohort(path)


def test_prepare_panel_null_source_fails_closed_on_cohort_or_history_mismatch() -> None:
    source = _source_panel()
    with pytest.raises(ValueError, match=r"missing symbols.*ZZZ"):
        prepare_panel_null_source(source, ("AAA", "ZZZ"), target_n_bars=5)
    with pytest.raises(ValueError, match=r"unexpected symbols.*BBB"):
        prepare_panel_null_source(source, ("AAA",), target_n_bars=5)
    with pytest.raises(ValueError, match="duplicate symbol"):
        prepare_panel_null_source(source, ("AAA", "AAA"), target_n_bars=5)
    with pytest.raises(ValueError, match=r"complete calendar has 4 rows.*requires 5"):
        incomplete = {symbol: frame.copy() for symbol, frame in source.items()}
        incomplete["AAA"].iloc[2, incomplete["AAA"].columns.get_loc("volume")] = np.nan
        incomplete["BBB"].iloc[4, incomplete["BBB"].columns.get_loc("close")] = np.nan
        prepare_panel_null_source(incomplete, ("AAA", "BBB"), target_n_bars=5)


def test_bind_panel_null_cohort_freezes_selection_and_prepared_source_identity() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    prepared = prepare_panel_null_source(_source_panel(), selected.symbols, target_n_bars=5)

    cohort = bind_panel_null_cohort(
        selected,
        prepared,
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-excess-v1",
        base_seed=17,
        code_revision="1" * 40,
    )

    assert cohort.symbols == selected.symbols
    assert cohort.symbol_excesses == selected.symbol_excesses
    assert cohort.target_n_bars == selected.target_n_bars
    assert cohort.history_tolerance == selected.history_tolerance
    assert cohort.search_config_version == selected.search_config_version
    assert cohort.gate_config_version == selected.gate_config_version
    assert cohort.source_start == prepared.source_start
    assert cohort.source_end == prepared.source_end
    assert cohort.source_sha256 == prepared.source_sha256
    assert cohort.n_replicates == 400
    assert cohort.min_successful_symbols == selected.min_symbols


def test_bind_panel_null_cohort_rejects_source_cohort_or_history_drift() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )

    wrong_order = prepare_panel_null_source(
        _source_panel(), tuple(reversed(selected.symbols)), target_n_bars=5
    )
    with pytest.raises(ValueError, match="ordered symbols"):
        bind_panel_null_cohort(
            selected,
            wrong_order,
            generator_version="joint-iid-calendar-v1",
            diagnostic_version="equal-symbol-excess-v1",
            base_seed=17,
            code_revision="1" * 40,
        )

    wrong_history = prepare_panel_null_source(_source_panel(), selected.symbols, target_n_bars=4)
    with pytest.raises(ValueError, match="target history"):
        bind_panel_null_cohort(
            selected,
            wrong_history,
            generator_version="joint-iid-calendar-v1",
            diagnostic_version="equal-symbol-excess-v1",
            base_seed=17,
            code_revision="1" * 40,
        )


def test_fetch_panel_null_source_fetches_each_frozen_symbol_once_in_order() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    source = _source_panel()
    fetched: list[str] = []

    def fetch_frame(symbol: str) -> pd.DataFrame:
        fetched.append(symbol)
        return source[symbol]

    prepared = fetch_panel_null_source(selected, fetch_frame)

    assert fetched == ["AAA", "BBB"]
    assert prepared.symbols == selected.symbols
    assert prepared.target_n_bars == selected.target_n_bars


def test_observed_panel_excess_is_remeasured_once_on_the_exact_prepared_source() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=9.0, walk_forward_hold=0.0, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=8.0, walk_forward_hold=0.0, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    prepared = prepare_panel_null_source(_source_panel(), selected.symbols, target_n_bars=5)
    searched: list[str] = []

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        searched.append(symbol)
        pd.testing.assert_frame_equal(frame, prepared.to_frames()[symbol])
        return _experiment(
            symbol,
            walk_forward=0.6 if symbol == "AAA" else 0.4,
            walk_forward_hold=0.2,
            purged_cv=0.5 if symbol == "AAA" else None,
            purged_cv_hold=0.1 if symbol == "AAA" else None,
            n_bars=5,
            search_version="search-v1",
            gate_config=gate,
        )

    measured = measure_observed_panel_excesses(selected, prepared, search=search)

    assert searched == ["AAA", "BBB"]
    assert [value.walk_forward for value in measured] == pytest.approx([0.4, 0.2])
    assert [value.purged_cv for value in measured] == [pytest.approx(0.4), None]
    assert measured != selected.symbol_excesses


def test_observed_panel_excess_fails_closed_on_missing_or_drifted_search_results() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.3, walk_forward_hold=0.1, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=0.3, walk_forward_hold=0.1, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    prepared = prepare_panel_null_source(_source_panel(), selected.symbols, target_n_bars=5)

    def missing_primary(frame: pd.DataFrame, symbol: str) -> Experiment:
        del frame
        return _experiment(
            symbol,
            walk_forward=None,
            walk_forward_hold=None,
            n_bars=5,
            search_version="search-v1",
            gate_config=gate,
        )

    with pytest.raises(ValueError, match=r"AAA.*missing paired walk-forward"):
        measure_observed_panel_excesses(selected, prepared, search=missing_primary)

    def wrong_history(frame: pd.DataFrame, symbol: str) -> Experiment:
        del frame
        return _experiment(
            symbol,
            walk_forward=0.3,
            walk_forward_hold=0.1,
            n_bars=4,
            search_version="search-v1",
            gate_config=gate,
        )

    with pytest.raises(ValueError, match=r"AAA.*history"):
        measure_observed_panel_excesses(selected, prepared, search=wrong_history)


def test_fetch_panel_null_source_reports_every_failed_symbol_without_preparing() -> None:
    selected = SelectedPanelNullCohort(
        symbols=("AAA", "BBB", "CCC"),
        symbol_excesses=tuple(
            PanelSymbolExcess(symbol=symbol, walk_forward=0.1) for symbol in ("AAA", "BBB", "CCC")
        ),
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version="gate-v1",
        min_symbols=3,
    )
    source = _source_panel()

    def fetch_frame(symbol: str) -> pd.DataFrame:
        if symbol == "BBB":
            raise RuntimeError("vendor unavailable")
        if symbol == "CCC":
            raise ValueError("symbol unavailable")
        return source[symbol]

    with pytest.raises(ValueError, match=r"BBB.*vendor unavailable.*CCC.*symbol unavailable"):
        fetch_panel_null_source(selected, fetch_frame)


def test_run_panel_null_replicate_searches_one_joint_panel_and_pairs_diagnostics() -> None:
    gate = GateConfig()
    selected = select_panel_null_cohort(
        [
            _experiment("AAA", walk_forward=0.4, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
            _experiment("BBB", walk_forward=0.5, walk_forward_hold=0.2, n_bars=5, gate_config=gate),
        ],
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    prepared = prepare_panel_null_source(_source_panel(), selected.symbols, target_n_bars=5)
    cohort = bind_panel_null_cohort(
        selected,
        prepared,
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-excess-v1",
        base_seed=17,
        code_revision="1" * 40,
    )
    searched: list[tuple[str, pd.DataFrame]] = []

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        searched.append((symbol, frame))
        offset = 0.1 if symbol == "AAA" else 0.2
        return _experiment(
            symbol,
            walk_forward=0.5 + offset,
            walk_forward_hold=0.1,
            purged_cv=0.4 + offset,
            purged_cv_hold=0.2,
            n_bars=5,
            gate_config=gate,
        )

    replicate = run_panel_null_replicate(cohort, prepared, panel_index=3, search=search)

    assert [symbol for symbol, _ in searched] == ["AAA", "BBB"]
    assert all(frame.index[0] == pd.Timestamp("2010-01-04", tz="UTC") for _, frame in searched)
    assert replicate.panel_index == 3
    assert replicate.seed == panel_seed(17, 3)
    assert replicate.successful_symbols == 2
    assert replicate.errors == ()
    assert replicate.walk_forward_excess == pytest.approx(0.55)
    assert replicate.purged_cv_excess == pytest.approx(0.35)


def test_run_panel_null_replicate_retains_failures_and_refuses_partial_secondary() -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=400, min_successful_symbols=1).model_copy(
        update={
            "symbols": ("AAA", "BBB"),
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": 5,
            "search_config_version": "search-v1",
            "gate_config_version": GateConfig().version_hash,
        }
    )

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        if symbol == "BBB":
            raise RuntimeError("search failed")
        return _experiment(
            symbol,
            walk_forward=0.6,
            walk_forward_hold=0.1,
            purged_cv=None,
            purged_cv_hold=None,
            n_bars=len(frame),
        )

    replicate = run_panel_null_replicate(cohort, prepared, panel_index=0, search=search)

    assert replicate.successful_symbols == 1
    assert [(error.symbol, error.message) for error in replicate.errors] == [
        ("BBB", "search failed")
    ]
    assert replicate.walk_forward_excess == pytest.approx(0.5)
    assert replicate.purged_cv_excess is None


def test_run_panel_null_replicate_rejects_source_or_search_identity_drift() -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=400).model_copy(
        update={
            "symbols": ("AAA", "BBB"),
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": 5,
        }
    )

    with pytest.raises(ValueError, match="source digest"):
        run_panel_null_replicate(
            cohort.model_copy(update={"source_sha256": "b" * 64}),
            prepared,
            panel_index=0,
            search=lambda frame, symbol: _experiment(
                symbol, walk_forward=0.6, walk_forward_hold=0.1, n_bars=len(frame)
            ),
        )

    with pytest.raises(ValueError, match="no measured symbols"):
        run_panel_null_replicate(
            cohort,
            prepared,
            panel_index=0,
            search=lambda frame, symbol: _experiment(
                symbol,
                walk_forward=0.6,
                walk_forward_hold=0.1,
                n_bars=len(frame),
                search_version="wrong-search",
            ),
        )


def test_run_panel_null_batch_executes_only_explicit_complete_indices(tmp_path: Path) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=4).model_copy(
        update={
            "symbols": prepared.symbols,
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": prepared.target_n_bars,
            "gate_config_version": GateConfig().version_hash,
        }
    )
    source_path = tmp_path / "prepared-panel.npz"
    shard_path = tmp_path / "panel-shard.json"
    save_prepared_panel_null_source(prepared, source_path)
    searched: list[str] = []

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        searched.append(symbol)
        return _experiment(
            symbol,
            walk_forward=0.6,
            walk_forward_hold=0.1,
            purged_cv=0.4,
            purged_cv_hold=0.2,
            n_bars=len(frame),
        )

    shard = run_panel_null_batch(
        cohort,
        source_path,
        panel_indices=(3, 1),
        output_path=shard_path,
        search=search,
    )

    assert tuple(replicate.panel_index for replicate in shard.replicates) == (1, 3)
    assert searched == ["AAA", "BBB", "AAA", "BBB"]
    assert load_panel_null_shard(shard_path) == shard


def test_run_panel_null_batch_rejects_ambiguous_indices_and_existing_output(
    tmp_path: Path,
) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=4).model_copy(
        update={
            "symbols": prepared.symbols,
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": prepared.target_n_bars,
        }
    )
    source_path = tmp_path / "prepared-panel.npz"
    output_path = tmp_path / "panel-shard.json"
    save_prepared_panel_null_source(prepared, source_path)
    output_path.write_text("owned", encoding="utf-8")
    called = False

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        nonlocal called
        called = True
        return _experiment(symbol, walk_forward=0.6, walk_forward_hold=0.1, n_bars=len(frame))

    with pytest.raises(ValueError, match="at least one explicit panel index"):
        run_panel_null_batch(
            cohort,
            source_path,
            panel_indices=(),
            output_path=tmp_path / "empty.json",
            search=search,
        )
    with pytest.raises(ValueError, match="duplicate panel index"):
        run_panel_null_batch(
            cohort,
            source_path,
            panel_indices=(1, 1),
            output_path=tmp_path / "duplicate.json",
            search=search,
        )
    with pytest.raises(ValueError, match="outside the frozen replicate range"):
        run_panel_null_batch(
            cohort,
            source_path,
            panel_indices=(4,),
            output_path=tmp_path / "outside.json",
            search=search,
        )
    with pytest.raises(FileExistsError):
        run_panel_null_batch(
            cohort,
            source_path,
            panel_indices=(0,),
            output_path=output_path,
            search=search,
        )
    assert called is False


def test_run_production_panel_null_batch_loads_frozen_inputs_and_executes(
    tmp_path: Path,
) -> None:
    gate = GateConfig()
    strategies = ["sma"]
    fingerprint = calibration_search_version(
        strategies,
        n_per_param=3,
        config=gate,
        refine=True,
        refine_span=0.25,
        select_by="observed",
    )
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=4).model_copy(
        update={
            "symbols": prepared.symbols,
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": prepared.target_n_bars,
            "search_config_version": fingerprint,
            "gate_config_version": gate.version_hash,
        }
    )
    cohort_path = tmp_path / "panel-cohort.json"
    source_path = tmp_path / "prepared-panel.npz"
    output_path = tmp_path / "panel-shard.json"
    save_panel_null_cohort(cohort, cohort_path)
    save_prepared_panel_null_source(prepared, source_path)
    calls: list[str] = []

    def fake_run_search(
        frame: pd.DataFrame, symbol: str, strategy_names: list[str], **kwargs: object
    ) -> Experiment:
        calls.append(symbol)
        return _experiment(
            symbol,
            walk_forward=0.6,
            walk_forward_hold=0.1,
            n_bars=len(frame),
            search_version=fingerprint,
            gate_config=gate,
        )

    shard = run_production_panel_null_batch(
        cohort_path,
        source_path,
        code_revision="1" * 40,
        strategy_names=strategies,
        config=gate,
        panel_indices=(2,),
        output_path=output_path,
        run_search_fn=fake_run_search,
    )

    assert tuple(replicate.panel_index for replicate in shard.replicates) == (2,)
    assert calls == ["AAA", "BBB"]
    assert load_panel_null_shard(output_path) == shard


def test_run_production_panel_null_batch_rejects_manifest_source_drift_before_search(
    tmp_path: Path,
) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort_path = tmp_path / "panel-cohort.json"
    source_path = tmp_path / "prepared-panel.npz"
    save_panel_null_cohort(
        _cohort(n_replicates=4).model_copy(
            update={
                "symbols": prepared.symbols,
                "source_start": prepared.source_start,
                "source_end": prepared.source_end,
                "source_sha256": "b" * 64,
                "target_n_bars": prepared.target_n_bars,
            }
        ),
        cohort_path,
    )
    save_prepared_panel_null_source(prepared, source_path)
    called = False

    def fake_run_search(
        frame: pd.DataFrame, symbol: str, strategy_names: list[str], **kwargs: object
    ) -> Experiment:
        nonlocal called
        called = True
        return _experiment(symbol, walk_forward=0.6, walk_forward_hold=0.1, n_bars=len(frame))

    with pytest.raises(ValueError, match="source digest"):
        run_production_panel_null_batch(
            cohort_path,
            source_path,
            code_revision="1" * 40,
            strategy_names=["sma"],
            config=GateConfig(),
            panel_indices=(0,),
            output_path=tmp_path / "panel-shard.json",
            run_search_fn=fake_run_search,
        )
    assert called is False


def test_run_production_panel_null_batch_rejects_code_revision_drift_before_search(
    tmp_path: Path,
) -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)
    cohort = _cohort(n_replicates=4).model_copy(
        update={
            "symbols": prepared.symbols,
            "source_start": prepared.source_start,
            "source_end": prepared.source_end,
            "source_sha256": prepared.source_sha256,
            "target_n_bars": prepared.target_n_bars,
        }
    )
    cohort_path = tmp_path / "panel-cohort.json"
    source_path = tmp_path / "prepared-panel.npz"
    save_panel_null_cohort(cohort, cohort_path)
    save_prepared_panel_null_source(prepared, source_path)
    called = False

    def fake_run_search(*args: object, **kwargs: object) -> Experiment:
        del args, kwargs
        nonlocal called
        called = True
        raise AssertionError("revision drift must fail before search")

    with pytest.raises(ValueError, match="code revision"):
        run_production_panel_null_batch(
            cohort_path,
            source_path,
            code_revision="2" * 40,
            strategy_names=["sma"],
            config=GateConfig(),
            panel_indices=(0,),
            output_path=tmp_path / "panel-shard.json",
            run_search_fn=fake_run_search,
        )
    assert called is False


def test_panel_null_shard_archive_is_exclusive_and_revalidates_payload(tmp_path: Path) -> None:
    shard = PanelNullShard(cohort=_cohort(), replicates=(_replicate(1), _replicate(3)))
    path = tmp_path / "panel-shard.json"

    save_panel_null_shard(shard, path)

    assert load_panel_null_shard(path) == shard
    with pytest.raises(FileExistsError):
        save_panel_null_shard(shard, path)

    tampered = shard.model_dump(mode="json")
    tampered["replicates"][0]["seed"] = panel_seed(99, 1)
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValidationError, match="derived seed"):
        load_panel_null_shard(path)

    with pytest.raises(ValidationError, match="at least one complete panel replicate"):
        PanelNullShard(cohort=_cohort(), replicates=())


def test_make_production_panel_null_search_pins_and_forwards_the_frozen_policy() -> None:
    gate = GateConfig()
    strategies = ["sma"]
    fingerprint = calibration_search_version(
        strategies,
        n_per_param=3,
        config=gate,
        refine=True,
        refine_span=0.25,
        select_by="observed",
    )
    selected = SelectedPanelNullCohort(
        symbols=("AAA", "BBB"),
        symbol_excesses=(
            PanelSymbolExcess(symbol="AAA", walk_forward=0.1),
            PanelSymbolExcess(symbol="BBB", walk_forward=0.2),
        ),
        target_n_bars=5,
        history_tolerance=0.10,
        search_config_version=fingerprint,
        gate_config_version=gate.version_hash,
        min_symbols=2,
    )
    calls: list[tuple[str, list[str], dict[str, object]]] = []

    def fake_run_search(
        frame: pd.DataFrame, symbol: str, strategy_names: list[str], **kwargs: object
    ) -> Experiment:
        calls.append((symbol, strategy_names, kwargs))
        return _experiment(
            symbol,
            walk_forward=0.6,
            walk_forward_hold=0.1,
            n_bars=len(frame),
            search_version=fingerprint,
            gate_config=gate,
        )

    search = make_production_panel_null_search(
        selected,
        strategies,
        config=gate,
        run_search_fn=fake_run_search,
    )
    frame = _source_panel()["AAA"]

    assert search(frame, "AAA").symbol == "AAA"
    assert calls == [
        (
            "AAA",
            ["sma"],
            {
                "config": gate,
                "prior_trials": 0,
                "n_per_param": 3,
                "refine": True,
                "refine_span": 0.25,
                "select_by": "observed",
            },
        )
    ]


def test_make_production_panel_null_search_rejects_identity_drift_before_execution() -> None:
    called = False

    def fake_run_search(
        frame: pd.DataFrame, symbol: str, strategy_names: list[str], **kwargs: object
    ) -> Experiment:
        nonlocal called
        called = True
        return _experiment(symbol, walk_forward=0.6, walk_forward_hold=0.1, n_bars=len(frame))

    with pytest.raises(ValueError, match="search policy does not match"):
        make_production_panel_null_search(
            _cohort(n_replicates=400),
            ["sma"],
            config=GateConfig(),
            run_search_fn=fake_run_search,
        )
    assert called is False

    matching_search = calibration_search_version(
        ["sma"],
        n_per_param=3,
        config=GateConfig(),
        refine=True,
        refine_span=0.25,
        select_by="observed",
    )
    with pytest.raises(ValueError, match="gate policy does not match"):
        make_production_panel_null_search(
            _cohort(n_replicates=400).model_copy(update={"search_config_version": matching_search}),
            ["sma"],
            config=GateConfig(),
            run_search_fn=fake_run_search,
        )
    assert called is False


def test_joint_iid_panel_null_uses_one_calendar_draw_for_every_symbol() -> None:
    source = _source_panel()
    generated = joint_iid_panel_null(source, 12, seed=23)

    aaa_rows = generated["AAA"]["volume"].to_numpy(dtype=int) - 1000
    bbb_rows = generated["BBB"]["volume"].to_numpy(dtype=int) - 2000
    assert np.array_equal(aaa_rows, bbb_rows)
    assert (aaa_rows >= 1).all()  # row zero has no close-to-close return to resample

    for symbol, frame in generated.items():
        base = float(source[symbol]["close"].iloc[0])
        reconstructed = np.r_[
            float(frame["close"].iloc[0]) / base - 1.0,
            frame["close"].pct_change().iloc[1:].to_numpy(),
        ]
        expected = source[symbol]["close"].pct_change().to_numpy()[aaa_rows]
        assert reconstructed == pytest.approx(expected)


def test_joint_iid_panel_null_reconstructs_same_bar_ohlcv_geometry() -> None:
    source = _source_panel()
    first = joint_iid_panel_null(source, 10, seed=31)
    second = joint_iid_panel_null(source, 10, seed=31)

    for symbol, frame in first.items():
        pd.testing.assert_frame_equal(frame, second[symbol])
        drawn_rows = frame["volume"].to_numpy(dtype=int) - (1000 if symbol == "AAA" else 2000)
        source_rows = source[symbol].iloc[drawn_rows]
        for column in ("open", "high", "low"):
            assert (frame[column] / frame["close"]).to_numpy() == pytest.approx(
                (source_rows[column] / source_rows["close"]).to_numpy()
            )
        assert np.isfinite(frame.to_numpy()).all()
        assert (frame[["open", "high", "low", "close"]] > 0).all().all()
        assert (frame["high"] >= frame[["open", "close"]].max(axis=1)).all()
        assert (frame["low"] <= frame[["open", "close"]].min(axis=1)).all()


def test_joint_iid_panel_null_rejects_unaligned_or_incomplete_sources() -> None:
    source = _source_panel()
    misaligned = {**source, "BBB": source["BBB"].iloc[1:]}
    with pytest.raises(ValueError, match="aligned"):
        joint_iid_panel_null(misaligned, 5, seed=1)

    naive = {symbol: frame.tz_localize(None) for symbol, frame in source.items()}
    with pytest.raises(ValueError, match="timezone-aware"):
        joint_iid_panel_null(naive, 5, seed=1)

    incomplete = {symbol: frame.copy() for symbol, frame in source.items()}
    incomplete["AAA"].iloc[2, incomplete["AAA"].columns.get_loc("volume")] = np.nan
    with pytest.raises(ValueError, match="finite"):
        joint_iid_panel_null(incomplete, 5, seed=1)

    with pytest.raises(ValueError, match="at least one symbol"):
        joint_iid_panel_null({}, 5, seed=1)
    with pytest.raises(ValueError, match="n_bars"):
        joint_iid_panel_null(source, 0, seed=1)


def test_panel_cohort_requires_exactly_one_value_per_ordered_symbol() -> None:
    cohort = _cohort()
    assert cohort.symbols == ("AAA", "BBB")
    assert (cohort.base_seed, cohort.n_replicates, cohort.min_successful_symbols) == (17, 4, 2)
    assert tuple(value.symbol for value in cohort.symbol_excesses) == cohort.symbols

    payload = cohort.model_dump()
    payload["symbol_excesses"] = tuple(reversed(payload["symbol_excesses"]))
    with pytest.raises(ValidationError, match="ordered symbols"):
        PanelNullCohort.model_validate(payload)


def test_panel_cohort_rejects_duplicate_symbols_and_invalid_source_digest() -> None:
    payload = _cohort().model_dump()
    payload["symbols"] = ("AAA", "AAA")
    with pytest.raises(ValidationError, match="duplicate"):
        PanelNullCohort.model_validate(payload)

    with pytest.raises(ValidationError, match="SHA-256"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "source_sha256": "abc"})


def test_panel_artifacts_are_frozen() -> None:
    cohort = _cohort()
    with pytest.raises(ValidationError, match="frozen"):
        cohort.target_n_bars = 5400  # type: ignore[misc]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_panel_artifacts_reject_non_finite_statistics(value: float) -> None:
    with pytest.raises(ValidationError, match="finite number"):
        PanelSymbolExcess(symbol="AAA", walk_forward=value, purged_cv=0.1)
    with pytest.raises(ValidationError, match="finite number"):
        PanelSymbolExcess(symbol="AAA", walk_forward=0.1, purged_cv=value)
    with pytest.raises(ValidationError, match="finite number"):
        PanelNullReplicate(
            panel_index=0,
            panel_id="panel-000",
            seed=panel_seed(17, 0),
            successful_symbols=2,
            walk_forward_excess=value,
            purged_cv_excess=0.1,
        )
    with pytest.raises(ValidationError, match="finite number"):
        PanelNullReplicate(
            panel_index=0,
            panel_id="panel-000",
            seed=panel_seed(17, 0),
            successful_symbols=2,
            walk_forward_excess=0.1,
            purged_cv_excess=value,
        )


@pytest.mark.parametrize(
    ("replicates", "message"),
    [
        ((_replicate(0),), "complete panel indices"),
        ((_replicate(1), _replicate(0)), "ordered by panel index"),
        (
            (
                _replicate(0),
                _replicate(1).model_copy(update={"seed": panel_seed(18, 1)}),
            ),
            "derived seed",
        ),
        (
            (
                _replicate(0),
                _replicate(1).model_copy(update={"panel_id": "panel-000"}),
            ),
            "duplicate panel id",
        ),
        (
            (_replicate(0), _replicate(1, successful_symbols=1)),
            "successful-symbol floor",
        ),
    ],
)
def test_direct_calibration_construction_cannot_bypass_merge_invariants(
    replicates: tuple[PanelNullReplicate, ...], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        PanelNullCalibration(cohort=_cohort(n_replicates=2), replicates=replicates)


def test_merge_sorts_complete_panel_units_by_global_index() -> None:
    merged = merge_panel_null_shards(
        (
            PanelNullShard(cohort=_cohort(), replicates=(_replicate(2), _replicate(0))),
            PanelNullShard(cohort=_cohort(), replicates=(_replicate(3), _replicate(1))),
        ),
    )

    assert tuple(rep.panel_index for rep in merged.replicates) == (0, 1, 2, 3)
    assert merged.cohort == _cohort()


def test_panel_seed_depends_only_on_base_seed_and_global_index() -> None:
    assert panel_seed(17, 2) == panel_seed(17, 2)
    assert len({panel_seed(17, index) for index in range(4)}) == 4
    assert panel_seed(18, 2) != panel_seed(17, 2)

    wrong_seed = _replicate(0).model_copy(update={"seed": panel_seed(18, 0)})
    with pytest.raises(ValueError, match="derived seed"):
        merge_panel_null_shards(
            (PanelNullShard(cohort=_cohort(n_replicates=1), replicates=(wrong_seed,)),)
        )


@pytest.mark.parametrize(
    ("replicates", "message"),
    [
        ((_replicate(0), _replicate(0)), "duplicate panel index"),
        ((_replicate(0), _replicate(2)), "outside the frozen replicate range"),
    ],
)
def test_merge_rejects_duplicate_or_missing_panel_indices(
    replicates: tuple[PanelNullReplicate, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        merge_panel_null_shards(
            (PanelNullShard(cohort=_cohort(n_replicates=2), replicates=replicates),),
        )


def test_merge_rejects_identity_drift_between_shards() -> None:
    with pytest.raises(ValueError, match="cohort identity"):
        merge_panel_null_shards(
            (
                PanelNullShard(cohort=_cohort(), replicates=(_replicate(0),)),
                PanelNullShard(cohort=_cohort(source_digest="b" * 64), replicates=(_replicate(1),)),
            ),
        )


def test_merge_rejects_partial_panels_and_duplicate_panel_ids() -> None:
    with pytest.raises(ValueError, match="successful-symbol floor"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1),
                    replicates=(_replicate(0, successful_symbols=1),),
                ),
            ),
        )


def test_merge_requires_each_replicate_to_account_for_the_frozen_cohort() -> None:
    missing_without_error = _replicate(0, successful_symbols=1)
    with pytest.raises(ValueError, match="account for every cohort symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(missing_without_error,),
                ),
            ),
        )

    unknown_error = missing_without_error.model_copy(
        update={"errors": (PanelNullError(symbol="ZZZ", message="unsearchable"),)}
    )
    with pytest.raises(ValueError, match="error symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(unknown_error,),
                ),
            ),
        )

    duplicate_errors = missing_without_error.model_copy(
        update={
            "successful_symbols": 0,
            "errors": (
                PanelNullError(symbol="AAA", message="first"),
                PanelNullError(symbol="AAA", message="second"),
            ),
        }
    )
    with pytest.raises(ValueError, match="duplicate error symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(duplicate_errors,),
                ),
            ),
        )

    duplicate_id = _replicate(1).model_copy(update={"panel_id": "panel-000"})
    with pytest.raises(ValueError, match="duplicate panel id"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=2),
                    replicates=(_replicate(0), duplicate_id),
                ),
            ),
        )


def test_merge_rejects_empty_shards_and_non_positive_contracts() -> None:
    with pytest.raises(ValueError, match="at least one shard"):
        merge_panel_null_shards(())
    with pytest.raises(ValidationError, match="n_replicates"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "n_replicates": 0})
    with pytest.raises(ValidationError, match="min_successful_symbols"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "min_successful_symbols": 0})
