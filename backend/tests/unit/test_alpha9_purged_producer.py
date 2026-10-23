"""ADR-350: captured Alpha9 runtime/domain and price-change hull, without Numba."""

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from tests.unit.test_high_purged_producer import panel, runtime

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional import purged, search
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.panel import long_short_weights
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.cross_sectional.strategies import alpha9_signal
from app.research.lab.gate import GateConfig
from app.validation.purged_cv import purged_cv_evaluate, purged_kfold_splits


def measure(window: int = 5, *, floor: int = 0, receipt: Any = ...) -> tuple[Any, Any]:
    prices = panel(300)
    strategy = default_strategies()["xs_alpha9"]
    configs = [({"window": window}, q) for q in (0.1, 0.3)]
    matrix = np.column_stack(
        [portfolio_returns(strategy.build(p)(prices), prices, quantile=q) for p, q in configs]
    )
    return purged.measure_family_purged(
        strategy,
        configs,
        prices,
        matrix,
        asset_returns(prices).mean(axis=1).to_numpy(),
        floor=floor,
        requested_folds=3,
        **({} if receipt is ... else {"high_runtime": receipt}),
    )


@pytest.mark.parametrize("window", [3, 5, 10])
def test_alpha9_support_adds_difference_and_previous_weight(window: int) -> None:
    assert purged.support_lag(
        default_strategies()["xs_alpha9"], [({"window": window}, 0.2)], panel()
    ) == (window + 1, None)


@pytest.mark.parametrize("window", [3, 5, 10])
def test_alpha9_actual_kept_fold_means_and_benchmark_pairing(window: int) -> None:
    d, result = measure(window, receipt=runtime())
    prices = panel(300)
    matrix = np.column_stack(
        [portfolio_returns(alpha9_signal(prices, window), prices, quantile=q) for q in (0.1, 0.3)]
    )
    splits = purged_kfold_splits(len(prices), 3, window + 1)
    expected = purged_cv_evaluate(
        matrix, splits, embargo=window + 1, benchmark=asset_returns(prices).mean(axis=1).to_numpy()
    )
    assert result == expected
    assert d.method == purged.ALPHA9_PURGED_METHOD
    assert d.dependency_rule == "rolling-alpha9-v1"
    assert d.max_price_lag == d.embargo == window + 1
    assert d.kept_fold_ordinals == tuple(j for j, (a, b) in enumerate(splits) if len(a) and len(b))
    assert d.mean_oos_hold_sharpe == expected.mean_oos_hold_sharpe


@pytest.mark.parametrize(
    "version,engine,reason",
    [("future", None, "unsupported_pandas_version"), ("3.0.6", True, "unsupported_rolling_engine")],
)
def test_alpha9_saved_unsafe_domain_cannot_be_replaced_by_safe_globals(
    version: str, engine: bool | None, reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late runtime read"))
    d, result = measure(receipt=runtime(version, engine))
    assert d.status == "unsupported" and d.reason == reason and result is None
    assert d.method != purged.ALPHA9_PURGED_METHOD
    assert d.mean_oos_sharpe is None and d.max_price_lag is None


def test_alpha9_saved_safe_domain_does_not_read_later_globals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late runtime read"))
    d, result = measure(receipt=runtime())
    assert d.status == "measured" and result is not None


def test_alpha9_missing_receipt_raises_but_custom_identity_stays_unsupported() -> None:
    with pytest.raises(ValueError, match="runtime receipt"):
        measure()
    strategy = replace(default_strategies()["xs_alpha9"], build=lambda p: lambda prices: prices)
    d, result = purged.measure_family_purged(
        strategy,
        [({"window": 5}, 0.1), ({"window": 5}, 0.3)],
        panel(300),
        np.zeros((300, 2)),
        np.zeros(300),
        floor=0,
        requested_folds=3,
    )
    assert d.reason == "unsupported_factory" and result is None


@pytest.mark.parametrize(
    "params", [{}, {"window": True}, {"window": 3.0}, {"window": 4}, {"window": 3, "skip": 0}]
)
def test_alpha9_unshipped_parameter_domains_remain_unsupported(params: dict[str, Any]) -> None:
    assert purged.support_lag(default_strategies()["xs_alpha9"], [(params, 0.2)], panel()) == (
        None,
        "unsupported_parameters",
    )


@pytest.mark.parametrize("dtype", ["float32", "Float64", "int64"])
def test_alpha9_unaudited_dtype_remains_unsupported(dtype: str) -> None:
    assert purged.support_lag(
        default_strategies()["xs_alpha9"], [({"window": 3}, 0.2)], panel().astype(dtype)
    ) == (None, "unsupported_price_dtype")


def test_alpha9_floor_never_shrinks_or_invents_no_fold_scores() -> None:
    d, result = measure(floor=1000, receipt=runtime())
    assert d.status == "no_usable_folds" and d.method == purged.ALPHA9_PURGED_METHOD
    assert d.max_price_lag == 6 and d.embargo == 1000 and d.kept_fold_ordinals == ()
    assert d.mean_oos_sharpe is None and d.mean_oos_hold_sharpe is None and result is None


def test_alpha9_numerical_measurement_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("actual Alpha9 numerical refusal")

    monkeypatch.setattr(purged, "purged_cv_evaluate", broken)
    with pytest.raises(ValueError, match="actual Alpha9 numerical refusal"):
        measure(receipt=runtime())


@pytest.mark.parametrize("during", [True, False])
def test_alpha9_capture_refuses_within_call_or_across_configs(
    during: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe, unsafe = runtime(), runtime(use_numba=True)
    seq = iter([safe, unsafe] if during else [safe, safe, unsafe, unsafe])
    monkeypatch.setattr(search, "capture_high_runtime", lambda: next(seq))
    with pytest.raises(ValueError, match=r"runtime.*changed|inconsistent.*runtime"):
        search.run_cross_sectional_search(
            panel(),
            ["xs_alpha9"],
            quantiles=(0.1, 0.3),
            config=GateConfig(trial_budget=6),
            purged_folds=3,
        )


@pytest.mark.parametrize("unsafe_alpha", [False, True])
def test_search_carries_independent_alpha9_and_high_domains(
    unsafe_alpha: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    safe, unsafe = runtime(), runtime(use_numba=True)
    alpha_domain = unsafe if unsafe_alpha else safe
    high_domain = safe if unsafe_alpha else unsafe
    # Allocation is canonical high first, then Alpha9; each receives six configs.
    receipts = iter([high_domain] * 12 + [alpha_domain] * 12)
    calls: list[Any] = []

    def capture() -> Any:
        value = next(receipts)
        calls.append(value)
        return value

    monkeypatch.setattr(search, "capture_high_runtime", capture)
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late runtime read"))
    exp = search.run_cross_sectional_search(
        panel(),
        ["xs_alpha9", "xs_52w_high", "xs_reversal"],
        quantiles=(0.1, 0.3),
        config=GateConfig(trial_budget=18),
        purged_folds=3,
    )
    assert len(calls) == 24
    rows = {t.strategy_name: t for t in exp.trials}
    alpha, high = rows["xs_alpha9"].purged_diagnostic, rows["xs_52w_high"].purged_diagnostic
    assert alpha is not None and high is not None
    measured, unmeasured = (high, alpha) if unsafe_alpha else (alpha, high)
    assert measured.status == "measured" and unmeasured.reason == "unsupported_rolling_engine"
    assert measured.method == (
        purged.HIGH_PURGED_METHOD if unsafe_alpha else purged.ALPHA9_PURGED_METHOD
    )
    assert rows["xs_reversal"].purged_diagnostic.method.endswith("continuation-v1")
    store = JsonFileCrossSectionalStore(tmp_path / "pool.json")
    store.add(exp)
    assert store.all()[0] == exp
    wire = _view(store.all()[0])
    assert CrossSectionalView.model_validate_json(wire.model_dump_json()) == wire


@pytest.mark.parametrize("floor", [0, 20])
def test_alpha9_allocated_maximum_excludes_unallocated_catalog_window(floor: int) -> None:
    prices = panel(300)
    strategy = default_strategies()["xs_alpha9"]
    configs = [({"window": 3}, 0.1), ({"window": 5}, 0.3)]
    matrix = np.column_stack(
        [portfolio_returns(strategy.build(p)(prices), prices, quantile=q) for p, q in configs]
    )
    d, result = purged.measure_family_purged(
        strategy,
        configs,
        prices,
        matrix,
        asset_returns(prices).mean(axis=1).to_numpy(),
        floor=floor,
        requested_folds=3,
        high_runtime=runtime(),
    )
    assert d.max_price_lag == 6 and d.embargo == max(floor, 6) and result is not None


@given(window=st.sampled_from([3, 5, 10]), quantile=st.sampled_from([0.1, 0.2, 0.3]))
@settings(max_examples=9, deadline=None)
def test_alpha9_oldest_endpoint_expired_prefix_current_endpoint_and_warmup(
    window: int, quantile: float
) -> None:
    t = window + 6
    rows = np.arange(t + 5, dtype=float)
    prices = pd.DataFrame({"A": 100 + rows, "B": 100 + 0.5 * rows, "C": 100 - 0.5 * rows})

    def calc(p: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series, pd.Series]:
        signal = alpha9_signal(p, window)
        weights = long_short_weights(signal, quantile)
        gross = (weights.shift(1).fillna(0) * asset_returns(p)).sum(axis=1)
        costs = weights.diff().abs().fillna(weights.abs()).sum(axis=1) * 0.001
        net = portfolio_returns(signal, p, quantile=quantile, cost_rate=0.001)
        pd.testing.assert_series_equal(net, gross - costs, check_exact=True)
        return signal, weights, gross, costs, net

    base = calc(prices)
    pd.testing.assert_frame_equal(
        base[0].iloc[1:window], -prices.diff().iloc[1:window], check_exact=True
    )
    assert base[0].iloc[0].isna().all() and base[3].iloc[1] > 0
    oldest = prices.copy()
    oldest.loc[t - window - 1, "A"] += 2
    changed = calc(oldest)
    assert not base[1].iloc[t - 1].equals(changed[1].iloc[t - 1])
    pd.testing.assert_series_equal(base[1].iloc[t], changed[1].iloc[t], check_exact=True)
    assert all(base[k].iloc[t] != changed[k].iloc[t] for k in (2, 3, 4))
    expired = prices.copy()
    expired.loc[: t - window - 2, "A"] += 2
    for a, b in zip(base, calc(expired), strict=True):
        np.testing.assert_array_equal(np.asarray(a.iloc[t]), np.asarray(b.iloc[t]))
    current = prices.copy()
    current.loc[t, "A"] = prices.loc[t - 1, "A"]
    for a, b in zip(base, calc(current), strict=True):
        if isinstance(a, pd.DataFrame):
            pd.testing.assert_frame_equal(a.iloc[:t], b.iloc[:t], check_exact=True)
        else:
            pd.testing.assert_series_equal(a.iloc[:t], b.iloc[:t], check_exact=True)
    assert base[4].iloc[t] != calc(current)[4].iloc[t]
    for stop in (window, t):
        pd.testing.assert_series_equal(
            base[4].iloc[:stop], calc(prices.iloc[:stop])[4], check_exact=True
        )


@given(window=st.sampled_from([3, 5, 10]))
def test_alpha9_embargo_separates_both_inclusive_price_hulls(window: int) -> None:
    lag = window + 1
    for embargo in (lag - 1, lag):
        train, test = purged_kfold_splits(120, 3, embargo)[1]
        left, right = int(train[train < test[0]][-1]), int(train[train > test[-1]][0])
        assert (left < int(test[0]) - lag) == (embargo == lag)
        assert (right - lag > int(test[-1])) == (embargo == lag)


@pytest.mark.parametrize("window", [3, 5, 10])
def test_alpha9_sliding_extrema_conditional_oracle(window: int) -> None:
    increments = np.resize(np.array([1.0, 1.0, 0.0, -1.0, -1.0, 2.0]), (40, 3))
    prices = pd.DataFrame(100 + increments.cumsum(axis=0))
    changes = prices.diff()
    expected = -changes.copy()
    for t in range(window, len(prices)):
        values = changes.iloc[t - window + 1 : t + 1].to_numpy()
        keep = (values.min(axis=0) > 0) | (values.max(axis=0) < 0)
        expected.iloc[t] = np.where(keep, changes.iloc[t], -changes.iloc[t])
    pd.testing.assert_frame_equal(alpha9_signal(prices, window), expected, check_exact=True)
