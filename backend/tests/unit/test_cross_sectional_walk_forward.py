"""ADR-321: paired family-local continuation evidence, without changing selection."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.backtesting.metrics import sharpe_ratio
from app.research.cross_sectional import search
from app.research.cross_sectional.engine import asset_returns, split_panel_holdout
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.lab.gate import GateConfig
from app.validation.deflated_sharpe import deflated_sharpe
from app.validation.parameter_stability import parameter_stability
from app.validation.pbo import probability_of_backtest_overfitting
from app.validation.report import ValidationReport
from app.validation.walk_forward import walk_forward_evaluate, walk_forward_splits

METHOD = "family-walk-forward-equal-weight-continuation-v1"


def _panel() -> pd.DataFrame:
    rows = np.arange(600, dtype=float)[:, None]
    symbols = np.arange(6, dtype=float)[None, :]
    returns = 0.0003 + 0.009 * np.sin(rows * 0.73 + symbols * 1.3)
    returns += 0.003 * np.cos(rows * 0.17 + symbols * 0.7)
    return pd.DataFrame(
        100 * np.cumprod(1 + returns, axis=0),
        index=pd.date_range("2020-01-01", periods=600, freq="B", tz="UTC"),
        columns=[f"S{i}" for i in range(6)],
    )


def _run(prices: pd.DataFrame) -> search.CrossSectionalExperiment:
    return search.run_cross_sectional_search(
        prices,
        strategy_names=["xs_reversal", "xs_momentum"],
        config=GateConfig(trial_budget=8),
        walk_forward_count=3,
        pbo_splits=4,
    )


def _trial() -> dict[str, Any]:
    return {
        "strategy_name": "xs_reversal",
        "parameters": {"lookback": 5, "quantile": 0.2},
        "observed_sharpe": 0.2,
        "deflated_sharpe": -0.3,
        "pbo": 0.5,
        "parameter_stability_score": 0.7,
        "walk_forward_oos_sharpe": -0.2,
    }


def _payload() -> dict[str, Any]:
    return {
        "universe_symbols": ["S0", "S1"],
        "strategy_names": ["xs_reversal"],
        "gate_config": GateConfig(),
        "trials": [_trial()],
        "lifetime_trials": 1,
        "walk_forward_method": METHOD,
        "walk_forward_hold_sharpe": 0.4,
        "walk_forward_n_bars": 20,
        "walk_forward_n_splits": 3,
    }


def test_public_search_evaluates_every_allocated_family_in_order_with_search_only_pairing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prices = _panel()
    in_sample, _ = split_panel_holdout(prices)
    expected_benchmark = asset_returns(in_sample).mean(axis=1).to_numpy()
    expected_splits = walk_forward_splits(len(in_sample), 3)
    columns: list[tuple[str, np.ndarray]] = []
    calls: list[tuple[np.ndarray, np.ndarray, Any]] = []
    reports: list[Any] = []
    original_returns, original_report = search._config_returns, search._build_report

    def record_returns(*args: Any, **kwargs: Any) -> pd.Series:
        result = original_returns(*args, **kwargs)
        if len(args[3]) == len(in_sample):
            columns.append((args[0].name, result.to_numpy().copy()))
        return result

    def record_evaluation(matrix: Any, splits: Any, *, benchmark: Any = None) -> Any:
        assert benchmark is not None
        np.testing.assert_array_equal(benchmark, expected_benchmark)
        assert benchmark[0] == 0.0
        for actual, expected in zip(splits, expected_splits, strict=True):
            np.testing.assert_array_equal(actual[0], expected[0])
            np.testing.assert_array_equal(actual[1], expected[1])
        result = walk_forward_evaluate(matrix, splits, benchmark=benchmark)
        calls.append((matrix.copy(), benchmark, result))
        return result

    def record_report(*args: Any, **kwargs: Any) -> Any:
        report = original_report(*args, **kwargs)
        reports.append(report)
        return report

    monkeypatch.setattr(search, "_config_returns", record_returns)
    monkeypatch.setattr(search, "_build_report", record_report)
    monkeypatch.setattr(search, "walk_forward_evaluate", record_evaluation, raising=False)
    result = _run(prices)

    assert len(calls) == len(result.trials) == 2
    assert [trial.strategy_name for trial in result.trials] == ["xs_momentum", "xs_reversal"]
    assert result.walk_forward_method == METHOD
    assert result.walk_forward_n_bars == len(in_sample)
    assert result.walk_forward_n_splits == 3
    assert calls[0][1] is calls[1][1]
    for trial, (matrix, _, evaluated), report in zip(result.trials, calls, reports, strict=True):
        expected_columns = [values for name, values in columns if name == trial.strategy_name]
        assert len(expected_columns) == trial.n_evaluated_configs
        np.testing.assert_array_equal(matrix, np.column_stack(expected_columns))
        assert matrix.shape[0] == len(in_sample)
        assert trial.walk_forward_oos_sharpe == evaluated.mean_oos_sharpe
        assert result.walk_forward_hold_sharpe == evaluated.mean_oos_hold_sharpe
        assert report.walk_forward == evaluated
        assert report.n_walk_forward_splits == evaluated.n_splits
        assert report.purged_cv is None and report.n_purged_folds > 0
        text = " ".join(report.flags).lower()
        assert "family" in text and "switch" in text and "snapshot" in text
        assert "purged" in text and "not measured" in text


def test_public_diagnostics_do_not_read_holdout_prices() -> None:
    prices = _panel()
    before = _run(prices)
    in_sample, holdout = split_panel_holdout(prices)
    changed = prices.copy()
    changed.loc[holdout.index] *= np.linspace(1, 2, len(holdout))[:, None]
    after = _run(changed)
    assert before.walk_forward_n_bars == after.walk_forward_n_bars == len(in_sample)
    assert before.walk_forward_hold_sharpe == after.walk_forward_hold_sharpe
    assert [t.walk_forward_oos_sharpe for t in before.trials] == [
        t.walk_forward_oos_sharpe for t in after.trials
    ]


def test_public_search_propagates_diagnostic_refusal_before_holdout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("nonconstant returns must have measurable finite Sharpe moments")

    def forbidden_holdout(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("unmeasurable diagnostic reached locked holdout")

    monkeypatch.setattr(search, "walk_forward_evaluate", refuse, raising=False)
    monkeypatch.setattr(search, "_score_holdout", forbidden_holdout)
    with pytest.raises(ValueError, match="measurable finite Sharpe moments"):
        _run(_panel())


def test_real_evaluator_refuses_unmeasurable_train_block_with_measurable_primary_report() -> None:
    # Whole-history and CSCV blocks have ordinary dispersion. The first WF train block is
    # nonconstant finite evidence whose native standard deviation underflows to zero.
    matrix = np.column_stack(
        [
            [0.01, -0.02, 0.03, -0.01] * 6,
            [-0.02, 0.03, 0.01, -0.01] * 6,
        ]
    )
    matrix[:8] *= 1e-198
    sharpes = [sharpe_ratio(pd.Series(matrix[:, column])) for column in range(2)]
    pbo = probability_of_backtest_overfitting(matrix, 4)
    dsr = deflated_sharpe(max(sharpes), 2, max(float(np.std(sharpes, ddof=1)), 1e-6))
    stability = parameter_stability(sharpes).stability_score
    prior_primary_report = ValidationReport(
        strategy_name="controlled",
        observed_sharpe=max(sharpes),
        deflated_sharpe=dsr,
        pbo=pbo,
        parameter_stability_score=stability,
        n_walk_forward_splits=len(walk_forward_splits(24, 2)),
        n_purged_folds=3,
    )
    assert prior_primary_report.walk_forward is None
    assert np.isfinite(matrix).all() and np.std(matrix[:8, 0], ddof=1) == 0
    with pytest.raises(ValueError, match="measurable finite Sharpe moments"):
        search._build_report(
            "controlled",
            matrix,
            sharpes,
            24,
            pbo_splits=4,
            walk_forward_count=2,
            purged_folds=3,
            embargo=2,
            benchmark=np.array([0.01, -0.02, 0.03, -0.01] * 6),
        )


@pytest.mark.parametrize("mismatch", ["unpaired", "benchmark", "split_count", "split_lengths"])
def test_public_producer_refuses_inconsistent_evaluated_family_evidence(
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    original = search._build_report
    seen = 0

    def inconsistent_report(*args: Any, **kwargs: Any) -> ValidationReport:
        nonlocal seen
        report = original(*args, **kwargs)
        seen += 1
        if seen != (1 if mismatch == "unpaired" else 2):
            return report
        assert report.walk_forward is not None
        payload = report.model_dump(round_trip=True)
        result = payload["walk_forward"]
        if mismatch == "unpaired":
            result["mean_oos_hold_sharpe"] = None
        elif mismatch == "benchmark":
            result["mean_oos_hold_sharpe"] += 1.0
        elif mismatch == "split_lengths":
            result["splits"][0]["n_test"] += 1
        else:
            # Get a fully valid result for different actual geometry, not an invalid mock object.
            result = walk_forward_evaluate(
                args[1],
                walk_forward_splits(args[3], 2),
                benchmark=kwargs["benchmark"],
            ).model_dump(round_trip=True)
            payload["n_walk_forward_splits"] = 2
        payload["walk_forward"] = result
        return ValidationReport.model_validate(payload)

    def forbidden_holdout(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("inconsistent family evidence reached holdout")

    monkeypatch.setattr(search, "_build_report", inconsistent_report)
    monkeypatch.setattr(search, "_score_holdout", forbidden_holdout)
    with pytest.raises(
        ValueError, match=r"paired benchmark|share evaluated geometry and benchmark"
    ):
        _run(_panel())


@given(scale=st.floats(0.5, 2, allow_nan=False), future=st.floats(-0.01, 0.01))
@settings(max_examples=20, deadline=None)
def test_report_uses_train_only_argmax_and_first_index_ties(scale: float, future: float) -> None:
    # Two identical train columns must pick index0, even when index1 wins the first test block.
    base = np.array([0.01, -0.02, 0.03, -0.01] * 6) * scale
    matrix = np.column_stack([base, base])
    matrix[8:16, 1] += 0.03
    benchmark = base * 0.4
    splits = walk_forward_splits(24, 2)
    expected = walk_forward_evaluate(matrix, splits, benchmark=benchmark)
    report = search._build_report(
        "controlled",
        matrix,
        [0.1, 0.2],
        24,
        pbo_splits=4,
        walk_forward_count=2,
        purged_folds=3,
        embargo=2,
        benchmark=benchmark,
    )
    assert report.walk_forward == expected
    assert report.walk_forward.splits[0].selected_config == 0
    changed = matrix.copy()
    changed[8:, 0] += future
    perturbed = search._build_report(
        "controlled",
        changed,
        [0.1, 0.2],
        24,
        pbo_splits=4,
        walk_forward_count=2,
        purged_folds=3,
        embargo=2,
        benchmark=benchmark,
    )
    assert perturbed.walk_forward.splits[0].selected_config == 0
    assert perturbed.walk_forward.splits[0].is_sharpe == expected.splits[0].is_sharpe


def test_measured_claim_roundtrips_and_freezes_caller_owned_trials(tmp_path: Path) -> None:
    payload = _payload()
    trial = search.CrossSectionalTrial.model_validate(payload["trials"][0])
    payload["trials"] = [trial]
    experiment = search.CrossSectionalExperiment.model_validate(payload)
    assert experiment.walk_forward_method == METHOD
    assert experiment.walk_forward_hold_sharpe == 0.4
    assert experiment.walk_forward_n_bars == 20
    assert experiment.walk_forward_n_splits == 3
    object.__setattr__(trial, "walk_forward_oos_sharpe", 99.0)
    assert experiment.trials[0].walk_forward_oos_sharpe == -0.2
    for store in (
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ):
        store.add(experiment)
        restored = store.all()[0]
        assert restored == experiment
        with pytest.raises(AttributeError, match="immutable"):
            restored.trials.clear()


@pytest.mark.parametrize("scalar", [None, -0.2])
def test_legacy_null_and_unpaired_scalars_remain_readable(scalar: float | None) -> None:
    payload = _payload()
    for field in (
        "walk_forward_method",
        "walk_forward_hold_sharpe",
        "walk_forward_n_bars",
        "walk_forward_n_splits",
    ):
        payload.pop(field)
    payload["trials"][0]["walk_forward_oos_sharpe"] = scalar
    restored = search.CrossSectionalExperiment.model_validate(payload)
    assert restored.walk_forward_method is None
    assert restored.walk_forward_hold_sharpe is None
    assert restored.trials[0].walk_forward_oos_sharpe == scalar


@pytest.mark.parametrize(
    "field", ["walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"]
)
def test_measured_claim_requires_all_pairing_and_geometry_fields(field: str) -> None:
    payload = _payload()
    payload.pop(field)
    with pytest.raises(ValidationError):
        search.CrossSectionalExperiment.model_validate(payload)


@pytest.mark.parametrize(
    "field", ["walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"]
)
def test_unattributed_new_pairing_fields_refuse(field: str) -> None:
    payload = _payload()
    payload.pop("walk_forward_method")
    for other in ("walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"):
        if other != field:
            payload.pop(other)
    with pytest.raises(ValidationError):
        search.CrossSectionalExperiment.model_validate(payload)


@pytest.mark.parametrize(
    "change",
    [
        {"walk_forward_method": "unknown"},
        {"walk_forward_hold_sharpe": float("nan")},
        {"walk_forward_hold_sharpe": float("inf")},
        {"trials": [], "strategy_names": []},
        {"trials": [{**_trial(), "walk_forward_oos_sharpe": None}]},
        {"walk_forward_n_bars": 3},
        {"walk_forward_n_splits": 0},
    ],
)
def test_incomplete_or_invalid_measured_claim_refuses(change: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        search.CrossSectionalExperiment.model_validate({**_payload(), **change})


@pytest.mark.parametrize("field", ["walk_forward_n_bars", "walk_forward_n_splits"])
@pytest.mark.parametrize("bad", [True, np.bool_(True), 3.0, "3", -1])
def test_geometry_requires_original_nonboolean_integral_counts(field: str, bad: Any) -> None:
    with pytest.raises(ValidationError):
        search.CrossSectionalExperiment.model_validate({**_payload(), field: bad})


def test_native_integral_geometry_normalizes() -> None:
    result = search.CrossSectionalExperiment.model_validate(
        {
            **_payload(),
            "walk_forward_n_bars": np.int64(20),
            "walk_forward_n_splits": np.int32(3),
        }
    )
    assert type(result.walk_forward_n_bars) is int
    assert type(result.walk_forward_n_splits) is int


@pytest.mark.parametrize(
    "field", ["walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"]
)
def test_stores_revalidate_unchecked_incomplete_measured_copies(tmp_path: Path, field: str) -> None:
    measured = search.CrossSectionalExperiment.model_validate(_payload())
    forged = measured.model_copy(update={field: None})
    for store in (
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ):
        with pytest.raises(ValidationError):
            store.add(forged)
        assert store.all() == []
