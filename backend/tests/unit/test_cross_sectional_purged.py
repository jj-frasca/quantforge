"""ADR-325: restricted source support and durable paired purged evidence."""

import importlib
from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional import search
from app.research.cross_sectional.engine import (
    asset_returns,
    portfolio_returns,
    split_panel_holdout,
)
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.lab.gate import GateConfig
from app.validation.purged_cv import purged_cv_evaluate, purged_kfold_splits


def module() -> Any:
    return importlib.import_module("app.research.cross_sectional.purged")


def panel(n: int = 1100) -> pd.DataFrame:
    r = np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            f"S{i}": 100 + r * (0.01 + i * 0.003) + np.sin(r * (0.17 + i * 0.013) + i)
            for i in range(6)
        },
        index=pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC"),
    )


def evidence(**updates: Any) -> dict[str, Any]:
    return dict(
        method="restricted-shift-family-purged-equal-weight-continuation-v1",
        status="measured",
        n_bars=100,
        requested_folds=5,
        floor=2,
        dependency_rule="shifted-reversal-v1",
        max_price_lag=6,
        embargo=6,
        kept_fold_ordinals=(0, 1, 2, 3, 4),
        mean_oos_sharpe=0.75,
        mean_oos_hold_sharpe=0.25,
        **updates,
    )


def trial(**updates: Any) -> search.CrossSectionalTrial:
    data = {
        "strategy_name": "xs_reversal",
        "parameters": {"lookback": 5, "quantile": 0.2},
        "observed_sharpe": 1.0,
        "deflated_sharpe": 0.5,
        "pbo": 0.1,
        "parameter_stability_score": 0.5,
        "purged_cv_oos_sharpe": 0.75,
    }
    data.update(updates)
    return search.CrossSectionalTrial(**data)


def test_stable_factory_identity_across_registry_calls() -> None:
    a, b = default_strategies(), default_strategies()
    for name in ("xs_momentum", "xs_reversal", "xs_short_term_reversal_1m"):
        assert a[name].build is b[name].build


@pytest.mark.parametrize(
    "name,params,lag",
    [
        ("xs_momentum", {"lookback": 126, "skip": 21}, 148),
        ("xs_reversal", {"lookback": 3}, 4),
        ("xs_short_term_reversal_1m", {"lookback": 63}, 64),
    ],
)
def test_known_factory_support_and_replaced_name_refusal(
    name: str, params: dict[str, int], lag: int
) -> None:
    strategy = default_strategies()[name]
    assert module().support_lag(strategy, [(params, 0.1), (params, 0.3)], panel())[0] == lag
    fake = replace(strategy, build=lambda p: lambda prices: prices)
    assert module().support_lag(fake, [(params, 0.2)], panel()) == (None, "unsupported_factory")


@pytest.mark.parametrize(
    "params", [{"lookback": 4}, {"lookback": True}, {"lookback": 3.0}, {"lookback": 3, "hidden": 1}]
)
def test_unshipped_parameter_domain_is_unsupported(params: dict[str, Any]) -> None:
    assert module().support_lag(default_strategies()["xs_reversal"], [(params, 0.2)], panel()) == (
        None,
        "unsupported_parameters",
    )


@pytest.mark.parametrize("dtype", ["float32", "Float64", "int64"])
def test_unsupported_native_price_dtype(dtype: str) -> None:
    p = panel().astype(dtype)
    assert module().support_lag(
        default_strategies()["xs_reversal"], [({"lookback": 3}, 0.2)], p
    ) == (None, "unsupported_price_dtype")


@pytest.mark.parametrize("name", ["xs_low_volatility", "xs_value"])
def test_rolling_and_static_factories_remain_unsupported(name: str) -> None:
    strategy = default_strategies(value_scores={"S0": 1.0})[name]
    assert module().support_lag(strategy, [(strategy.param_grid[0], 0.2)], panel()) == (
        None,
        "unsupported_factory",
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("n_bars", True),
        ("n_bars", 100.0),
        ("requested_folds", 1),
        ("floor", -1),
        ("embargo", 6.0),
        ("max_price_lag", False),
        ("kept_fold_ordinals", (0, 1, True, 3, 4)),
        ("kept_fold_ordinals", (0, 1, 2, 3, 3)),
        ("kept_fold_ordinals", (0, 1, 2, 3)),
        ("embargo", 5),
        ("mean_oos_hold_sharpe", None),
        ("mean_oos_sharpe", np.inf),
        ("reason", "unsupported_factory"),
        ("method", "unknown"),
    ],
)
def test_durable_evidence_rejects_contradictions(field: str, value: Any) -> None:
    data = evidence()
    data[field] = value
    with pytest.raises(ValueError):
        module().PurgedDiagnostic(**data)


def test_nested_scalar_binding_and_legacy_unpaired() -> None:
    diagnostic = module().PurgedDiagnostic(**evidence())
    t = trial(purged_diagnostic=diagnostic)
    assert t.purged_diagnostic == diagnostic
    assert trial().purged_cv_oos_sharpe == 0.75
    with pytest.raises(ValueError):
        trial(purged_diagnostic=diagnostic, purged_cv_oos_sharpe=0.5)
    with pytest.raises(ValueError):
        trial(purged_diagnostic=diagnostic.model_copy(update={"mean_oos_hold_sharpe": np.nan}))
    with pytest.raises(ValueError):
        t.purged_diagnostic.kept_fold_ordinals += (5,)


def test_huge_geometry_is_allocation_free(monkeypatch: pytest.MonkeyPatch) -> None:
    m = module()
    n = 10**100

    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("persisted geometry allocated arrays")

    monkeypatch.setattr(np, "arange", forbidden)
    d = evidence()
    d.update(n_bars=n, requested_folds=n, floor=n - 2, embargo=n - 2, kept_fold_ordinals=(0, n - 1))
    assert m.PurgedDiagnostic(**d).kept_fold_ordinals == (0, n - 1)
    d.update(
        status="no_usable_folds",
        floor=n,
        embargo=n,
        kept_fold_ordinals=(),
        mean_oos_sharpe=None,
        mean_oos_hold_sharpe=None,
    )
    assert m.PurgedDiagnostic(**d).kept_fold_ordinals == ()


@given(n=st.integers(2, 70), k=st.integers(2, 70), e=st.integers(0, 80))
def test_closed_kept_geometry_matches_existing_splitter(n: int, k: int, e: int) -> None:
    if k > n:
        k = n
    actual = tuple(
        i
        for i, (train, test) in enumerate(purged_kfold_splits(n, k, e))
        if len(train) and len(test)
    )
    p, s, count = module().kept_geometry(n, k, e)
    assert count == len(actual)
    assert actual == tuple(i for i in range(k) if i < p or i >= s)


def test_direct_measurement_uses_allocated_lag_and_exact_kept_benchmark() -> None:
    m = module()
    p = panel(500)
    registry = default_strategies()
    b = asset_returns(p).mean(axis=1).to_numpy()
    outcomes = []
    for name, params in [
        ("xs_momentum", {"lookback": 252, "skip": 21}),
        ("xs_reversal", {"lookback": 3}),
    ]:
        configs = [(params, 0.1), (params, 0.3)]
        matrix = np.column_stack(
            [
                portfolio_returns(registry[name].build(pa)(p), p, quantile=q).to_numpy()
                for pa, q in configs
            ]
        )
        d, result = m.measure_family_purged(
            registry[name], configs, p, matrix, b, floor=2, requested_folds=5
        )
        expected = purged_cv_evaluate(
            matrix, purged_kfold_splits(len(p), 5, d.embargo), embargo=d.embargo, benchmark=b
        )
        assert result == expected
        assert d.mean_oos_hold_sharpe == expected.mean_oos_hold_sharpe
        assert d.max_price_lag == (274 if name == "xs_momentum" else 4)
        outcomes.append(d)
    assert outcomes[0].kept_fold_ordinals != outcomes[1].kept_fold_ordinals


def test_no_fold_preflight_and_numeric_failure_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    m = module()
    p = panel(100)
    s = default_strategies()["xs_momentum"]
    configs = [({"lookback": 252, "skip": 21}, 0.1), ({"lookback": 252, "skip": 21}, 0.3)]
    matrix = np.column_stack([np.arange(100) * 0.0001, np.arange(100) * -0.0001])
    b = np.zeros(100)

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("genuine measurement failure")

    monkeypatch.setattr(m, "purged_cv_evaluate", broken)
    d, result = m.measure_family_purged(s, configs, p, matrix, b, floor=2, requested_folds=5)
    assert d.status == "no_usable_folds" and result is None and d.kept_fold_ordinals == ()
    with pytest.raises(ValueError, match="genuine measurement failure"):
        m.measure_family_purged(
            s,
            configs,
            panel(700),
            np.tile(matrix, (7, 1)),
            np.zeros(700),
            floor=2,
            requested_folds=5,
        )
    matrix[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        m.measure_family_purged(s, configs, p, matrix, b, floor=2, requested_folds=5)


@pytest.mark.parametrize(
    "field,value",
    [
        ("embargo", True),
        ("embargo", 2.0),
        ("purged_folds", True),
        ("purged_folds", 2.0),
        ("purged_folds", 1),
    ],
)
def test_request_original_counts_refuse_before_panel_access(field: str, value: Any) -> None:
    with pytest.raises(ValueError, match=r"embargo|purged_folds"):
        search.run_cross_sectional_search(None, **{field: value})


def test_public_producer_all_branches_and_ephemeral_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reports = []
    original = search.GraduationGate.evaluate

    def capture(self: Any, **kwargs: Any) -> Any:
        reports.append(kwargs["report"])
        return original(self, **kwargs)

    monkeypatch.setattr(search.GraduationGate, "evaluate", capture)
    e = search.run_cross_sectional_search(
        panel(), strategy_names=["xs_reversal"], quantiles=(0.1, 0.3), walk_forward_count=3
    )
    t = e.trials[0]
    d = t.purged_diagnostic
    assert d.status == "measured" and d.n_bars == e.walk_forward_n_bars
    assert t.purged_cv_oos_sharpe == d.mean_oos_sharpe
    assert d.max_price_lag == 11
    assert reports[0].purged_cv.mean_oos_sharpe == d.mean_oos_sharpe
    assert reports[0].n_purged_folds == len(d.kept_fold_ordinals)
    assert not any("not measured" in f and "Purged" in f for f in reports[0].flags)
    other = search.run_cross_sectional_search(
        panel(), strategy_names=["xs_low_volatility"], quantiles=(0.1, 0.3), walk_forward_count=3
    )
    assert other.trials[0].purged_diagnostic.status == "unsupported"
    assert other.trials[0].purged_cv_oos_sharpe is None


def test_partial_budget_maximum_tracks_only_allocated_configs() -> None:
    e = search.run_cross_sectional_search(
        panel(),
        strategy_names=["xs_momentum"],
        config=GateConfig(trial_budget=2),
        quantiles=(0.1, 0.3),
        walk_forward_count=3,
    )
    assert e.trials[0].n_evaluated_configs == 2
    assert e.trials[0].purged_diagnostic.max_price_lag < 274


def test_experiment_complete_request_geometry_and_forged_store_refusal(tmp_path: Any) -> None:
    d = module().PurgedDiagnostic(**evidence())
    a = trial(purged_diagnostic=d)
    b = trial(strategy_name="xs_reversal_other", purged_cv_oos_sharpe=None)
    base = {
        "universe_symbols": ["S0"],
        "strategy_names": [a.strategy_name, b.strategy_name],
        "trials": [a, b],
        "gate_config": GateConfig(),
        "lifetime_trials": 2,
    }
    with pytest.raises(ValueError):
        search.CrossSectionalExperiment(**base)
    single = search.CrossSectionalExperiment(
        **{**base, "strategy_names": [a.strategy_name], "trials": [a]}
    )
    assert search.CrossSectionalExperiment.model_validate_json(single.model_dump_json()) == single
    bad = a.model_copy(update={"purged_cv_oos_sharpe": 0.5})
    forged = single.model_copy(update={"trials": [bad]})
    for store in (
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ):
        with pytest.raises(ValueError):
            store.add(forged)
        assert store.all() == []
    b = trial(purged_diagnostic=d.model_copy(update={"floor": 3}))
    with pytest.raises(ValueError):
        search.CrossSectionalExperiment(**{**base, "trials": [a, b]})


def test_experiment_pcv_bars_bind_to_attributed_walk_forward() -> None:
    diagnostic = module().PurgedDiagnostic(**evidence())
    t = trial(purged_diagnostic=diagnostic, walk_forward_oos_sharpe=0.1)
    with pytest.raises(ValueError, match="bars"):
        search.CrossSectionalExperiment(
            universe_symbols=["S0"],
            strategy_names=[t.strategy_name],
            trials=[t],
            gate_config=GateConfig(),
            lifetime_trials=1,
            walk_forward_method="family-walk-forward-equal-weight-continuation-v1",
            walk_forward_n_bars=101,
            walk_forward_n_splits=3,
            walk_forward_hold_sharpe=0.1,
        )


def test_allocated_matrix_order_first_ties_and_holdout_exclusion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    m = module()
    p = panel(100)
    configs = [({"lookback": 3}, 0.1), ({"lookback": 5}, 0.3)]
    d, result = m.measure_family_purged(
        default_strategies()["xs_reversal"],
        configs,
        p,
        np.zeros((100, 2)),
        np.zeros(100),
        floor=0,
        requested_folds=5,
    )
    assert result is not None and all(f.selected_config == 0 for f in result.folds)
    assert d.mean_oos_sharpe == d.mean_oos_hold_sharpe == 0
    original = search.measure_family_purged
    seen = []

    def capture(
        strategy: Any, configs: Any, prices: Any, matrix: Any, benchmark: Any, **kwargs: Any
    ) -> Any:
        seen.append((prices.copy(), matrix.copy(), benchmark.copy()))
        return original(strategy, configs, prices, matrix, benchmark, **kwargs)

    monkeypatch.setattr(search, "measure_family_purged", capture)
    source = panel()
    in_sample, holdout = split_panel_holdout(source)
    search.run_cross_sectional_search(
        source, strategy_names=["xs_reversal"], quantiles=(0.1, 0.3), walk_forward_count=3
    )
    assert len(seen) == 1
    actual, matrix, benchmark = seen[0]
    pd.testing.assert_frame_equal(actual, in_sample)
    assert not actual.index.isin(holdout.index).any()
    np.testing.assert_array_equal(benchmark, asset_returns(in_sample).mean(axis=1).to_numpy())
    registry = default_strategies()["xs_reversal"]
    expected = np.column_stack(
        [
            portfolio_returns(registry.build(params)(in_sample), in_sample, quantile=q).to_numpy()
            for params in registry.param_grid
            for q in (0.1, 0.3)
        ]
    )
    np.testing.assert_array_equal(matrix, expected)


@pytest.mark.parametrize("name", ["xs_momentum", "xs_reversal", "xs_short_term_reversal_1m"])
def test_supported_operand_endpoints_and_old_future_controls(name: str) -> None:
    p = panel(1000)
    old = p.copy()
    old.iloc[1, 0] *= 1000
    future = p.copy()
    future.iloc[800:, 1] *= 3
    strategy = default_strategies()[name]
    for params in strategy.param_grid:
        lag, _ = module().support_lag(strategy, [(params, 0.2)], p)
        assert lag is not None
        a = 2 * lag + 50
        b = a + 20
        skip = params.get("skip", 0)
        lookback = params["lookback"]

        def operands(t: int, skip: int = skip, lookback: int = lookback) -> set[int]:
            return {t, t - 1, t - skip, t - skip - lookback, t - 1 - skip, t - 1 - skip - lookback}

        test = set().union(*(operands(t) for t in range(a, b + 1)))
        assert operands(a - lag) & test == {a - lag}
        assert operands(b + lag) & test == {b}
        assert not operands(a - lag - 1) & test and not operands(b + lag + 1) & test
        f = strategy.build(params)
        s = f(p)
        pd.testing.assert_frame_equal(s.iloc[lag + 4 :], f(old).iloc[lag + 4 :], check_exact=True)
        pd.testing.assert_frame_equal(s.iloc[:800], f(future).iloc[:800], check_exact=True)
        x = portfolio_returns(s, p, quantile=0.2)
        pd.testing.assert_series_equal(
            x.iloc[lag + 4 :],
            portfolio_returns(f(old), old, quantile=0.2).iloc[lag + 4 :],
            check_exact=True,
        )
        pd.testing.assert_series_equal(
            x.iloc[:800],
            portfolio_returns(f(future), future, quantile=0.2).iloc[:800],
            check_exact=True,
        )


@pytest.mark.parametrize(
    "updates",
    [
        {"status": "unsupported", "reason": "unsupported_factory"},
        {"status": "no_usable_folds"},
        {"dependency_rule": "shifted-momentum-v1"},
    ],
)
def test_current_trial_refuses_false_branch_or_family_binding(updates: dict[str, Any]) -> None:
    payload = evidence()
    payload.update(updates)
    with pytest.raises(ValueError):
        trial(purged_diagnostic=payload)


def test_measured_lag_cannot_omit_finalist_dependency() -> None:
    payload = evidence()
    payload.update(max_price_lag=4, embargo=4)
    with pytest.raises(ValueError, match="finalist"):
        trial(purged_diagnostic=payload)


@pytest.mark.parametrize("lookback,skip", [(147, 0), (126, 84), (125, 22)])
def test_momentum_finalist_requires_each_shipped_parameter(lookback: int, skip: int) -> None:
    payload = evidence()
    payload.update(
        n_bars=1100,
        dependency_rule="shifted-momentum-v1",
        max_price_lag=274,
        embargo=274,
    )
    with pytest.raises(ValueError, match="finalist"):
        trial(
            strategy_name="xs_momentum",
            parameters={"lookback": lookback, "skip": skip, "quantile": 0.2},
            purged_diagnostic=payload,
        )


def test_complete_same_request_evidence_refuses_mixed_floors() -> None:
    a = trial(purged_diagnostic=evidence())
    payload = evidence()
    payload["floor"] = 3
    b = trial(purged_diagnostic=payload)
    with pytest.raises(ValueError, match="same request"):
        search.CrossSectionalExperiment(
            universe_symbols=["S0"],
            strategy_names=[a.strategy_name, b.strategy_name],
            trials=[a, b],
            gate_config=GateConfig(),
            lifetime_trials=2,
        )


def test_supported_measurement_requires_valid_price_source_before_no_fold() -> None:
    p = panel(100)
    p.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="prices"):
        module().measure_family_purged(
            default_strategies()["xs_reversal"],
            [({"lookback": 3}, 0.1), ({"lookback": 3}, 0.3)],
            p,
            np.zeros((100, 2)),
            np.zeros(100),
            floor=1000,
            requested_folds=5,
        )


def test_stable_wrappers_preserve_lazy_parameter_capture() -> None:
    p = panel(500)
    for name in ("xs_momentum", "xs_reversal", "xs_short_term_reversal_1m"):
        strategy = default_strategies()[name]
        params = dict(strategy.param_grid[0])
        signal = strategy.build(params)
        params["lookback"] = strategy.param_grid[-1]["lookback"]
        pd.testing.assert_frame_equal(signal(p), strategy.build(params)(p), check_exact=True)


@given(
    name=st.sampled_from(["xs_momentum", "xs_reversal", "xs_short_term_reversal_1m"]),
    config_index=st.integers(0, 20),
    old_row=st.integers(0, 12),
    multiplier=st.integers(2, 100),
)
def test_supported_source_operand_invariance_property(
    name: str, config_index: int, old_row: int, multiplier: int
) -> None:
    prices = panel(800)
    strategy = default_strategies()[name]
    params = strategy.param_grid[config_index % len(strategy.param_grid)]
    lag, _ = module().support_lag(strategy, [(params, 0.2)], prices)
    assert lag is not None
    signal = strategy.build(params)
    old = prices.copy()
    old.iloc[old_row, 0] *= multiplier
    start = old_row + lag + 3
    original = portfolio_returns(signal(prices), prices, quantile=0.2)
    changed = portfolio_returns(signal(old), old, quantile=0.2)
    pd.testing.assert_series_equal(original.iloc[start:], changed.iloc[start:], check_exact=True)
    future = prices.copy()
    future.iloc[700:, 1] *= multiplier
    pd.testing.assert_series_equal(
        original.iloc[:700],
        portfolio_returns(signal(future), future, quantile=0.2).iloc[:700],
        check_exact=True,
    )


def test_public_no_fold_report_has_zero_evaluated_count(monkeypatch: pytest.MonkeyPatch) -> None:
    original = search.GraduationGate.evaluate
    captured = []

    def capture(self: Any, **kwargs: Any) -> Any:
        captured.append(kwargs["report"])
        return original(self, **kwargs)

    monkeypatch.setattr(search.GraduationGate, "evaluate", capture)
    result = search.run_cross_sectional_search(
        panel(),
        strategy_names=["xs_reversal"],
        quantiles=(0.1, 0.3),
        embargo=10000,
        walk_forward_count=3,
    )
    diagnostic = result.trials[0].purged_diagnostic
    assert diagnostic.status == "no_usable_folds"
    assert diagnostic.kept_fold_ordinals == ()
    assert result.trials[0].purged_cv_oos_sharpe is None
    assert captured[0].n_purged_folds == 0 and captured[0].purged_cv is None
    assert any("no_usable_folds" in flag for flag in captured[0].flags)
