"""ADR-353 dedicated captured callback domain; unsafe tests use metadata only."""

from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_high_purged_producer import panel

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional import purged, search
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.panel import long_short_weights
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.cross_sectional.strategies import alpha4_signal
from app.research.lab.gate import GateConfig
from app.validation.purged_cv import purged_cv_evaluate, purged_kfold_splits


def runtime(
    pandas_version: str = "3.0.6", numpy_version: str = "2.5.4", use_numba: bool | None = False
) -> Any:
    cls = getattr(purged, "Alpha4Runtime", SimpleNamespace)
    return cls(pandas_version=pandas_version, numpy_version=numpy_version, use_numba=use_numba)


def measure(
    *, windows: tuple[int, ...] = (5, 9), floor: int = 0, receipt: Any = ...
) -> tuple[Any, Any]:
    prices = panel(300)
    strategy = default_strategies()["xs_alpha4"]
    configs = [({"window": w}, q) for w in windows for q in (0.1, 0.3)]
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
        **({} if receipt is ... else {"alpha4_runtime": receipt}),
    )


def test_alpha4_runtime_capture_and_frozen_identity() -> None:
    capture = getattr(purged, "capture_alpha4_runtime", None)
    assert capture is not None
    observed = capture()
    assert observed == runtime(pd.__version__, np.__version__, pd.get_option("compute.use_numba"))
    with pytest.raises(FrozenInstanceError):
        observed.numpy_version = "other"


@pytest.mark.parametrize("window", [5, 9, 21])
def test_alpha4_actual_lag_and_evaluator_pairing(window: int) -> None:
    strategy = default_strategies()["xs_alpha4"]
    assert purged.support_lag(strategy, [({"window": window}, 0.2)], panel()) == (window, None)
    d, result = measure(windows=(window,), receipt=runtime())
    prices = panel(300)
    matrix = np.column_stack(
        [portfolio_returns(alpha4_signal(prices, window), prices, quantile=q) for q in (0.1, 0.3)]
    )
    splits = purged_kfold_splits(300, 3, window)
    expected = purged_cv_evaluate(
        matrix, splits, embargo=window, benchmark=asset_returns(prices).mean(axis=1).to_numpy()
    )
    assert result == expected and d.method == purged.ALPHA4_PURGED_METHOD
    assert d.dependency_rule == "rolling-alpha4-percentile-v1"
    assert d.max_price_lag == d.embargo == window
    assert d.mean_oos_hold_sharpe == expected.mean_oos_hold_sharpe
    assert d.kept_fold_ordinals == tuple(j for j, (a, b) in enumerate(splits) if len(a) and len(b))


@pytest.mark.parametrize(
    "receipt,reason",
    [
        (runtime("future", "future", True), "unsupported_pandas_version"),
        (runtime(numpy_version="future", use_numba=True), "unsupported_numpy_version"),
        (runtime(use_numba=True), "unsupported_rolling_engine"),
    ],
)
def test_alpha4_saved_unsafe_receipts_precedence_and_no_late_reads(
    receipt: Any, reason: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        purged, "capture_alpha4_runtime", lambda: pytest.fail("late read"), raising=False
    )
    d, result = measure(receipt=receipt)
    assert d.status == "unsupported" and d.reason == reason and result is None
    assert d.method.endswith("continuation-v1") and d.mean_oos_sharpe is None


def test_alpha4_saved_safe_receipt_does_not_read_globals(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        purged, "capture_alpha4_runtime", lambda: pytest.fail("late read"), raising=False
    )
    d, result = measure(receipt=runtime())
    assert d.status == "measured" and result is not None


@pytest.mark.parametrize("receipt", [None, purged.HighRuntime("3.0.6", False)])
def test_alpha4_measurement_requires_dedicated_receipt(receipt: Any) -> None:
    with pytest.raises(ValueError, match="runtime receipt"):
        measure(receipt=receipt)


def test_alpha4_missing_receipt_and_custom_identity_precedence() -> None:
    with pytest.raises(ValueError, match="runtime receipt"):
        measure()
    strategy = replace(default_strategies()["xs_alpha4"], build=lambda p: lambda prices: prices)
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
    "params", [{}, {"window": True}, {"window": 5.0}, {"window": 3}, {"window": 5, "skip": 0}]
)
def test_alpha4_unshipped_parameters_stay_unsupported(params: Any) -> None:
    assert purged.support_lag(default_strategies()["xs_alpha4"], [(params, 0.2)], panel()) == (
        None,
        "unsupported_parameters",
    )


@pytest.mark.parametrize("dtype", ["float32", "Float64", "int64"])
def test_alpha4_unaudited_dtype_stays_unsupported(dtype: str) -> None:
    assert purged.support_lag(
        default_strategies()["xs_alpha4"], [({"window": 5}, 0.2)], panel().astype(dtype)
    ) == (None, "unsupported_price_dtype")


def test_alpha4_actual_allocation_floor_and_no_fold() -> None:
    d, result = measure(receipt=runtime())
    assert d.max_price_lag == 9 and d.embargo == 9 and result is not None
    d, result = measure(floor=1000, receipt=runtime())
    assert d.max_price_lag == 9 and d.embargo == 1000 and d.status == "no_usable_folds"
    assert d.kept_fold_ordinals == () and d.mean_oos_sharpe is None and result is None


def test_alpha4_evaluator_numerical_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("Alpha4 numerical refusal")

    monkeypatch.setattr(purged, "purged_cv_evaluate", broken)
    with pytest.raises(ValueError, match="Alpha4 numerical refusal"):
        measure(receipt=runtime())


@pytest.mark.parametrize(
    "unsafe", [runtime("future"), runtime(numpy_version="future"), runtime(use_numba=True)]
)
@pytest.mark.parametrize("during", [True, False])
def test_alpha4_capture_rejects_every_identity_drift(
    unsafe: Any, during: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    safe = runtime()
    sequence = iter([safe, unsafe] if during else [safe, safe, unsafe, unsafe])
    monkeypatch.setattr(search, "capture_alpha4_runtime", lambda: next(sequence), raising=False)
    with pytest.raises(ValueError, match=r"Alpha4.*runtime.*changed"):
        search.run_cross_sectional_search(
            panel(),
            ["xs_alpha4"],
            quantiles=(0.1, 0.3),
            config=GateConfig(trial_budget=6),
            purged_folds=3,
        )


@pytest.mark.parametrize("unsafe_alpha4", [True, False])
def test_alpha4_separate_saved_slots_coexist_with_high_and_alpha9(
    unsafe_alpha4: bool, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    a = runtime(numpy_version="future") if unsafe_alpha4 else runtime()
    h = purged.HighRuntime("3.0.6", not unsafe_alpha4)
    calls = {"alpha4": 0, "high": 0}

    def capture_a() -> Any:
        calls["alpha4"] += 1
        return a

    def capture_h() -> Any:
        calls["high"] += 1
        return h

    monkeypatch.setattr(search, "capture_alpha4_runtime", capture_a, raising=False)
    monkeypatch.setattr(search, "capture_high_runtime", capture_h)
    monkeypatch.setattr(
        purged, "capture_alpha4_runtime", lambda: pytest.fail("late Alpha4"), raising=False
    )
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late high"))
    exp = search.run_cross_sectional_search(
        panel(),
        ["xs_alpha4", "xs_alpha9", "xs_52w_high", "xs_reversal"],
        quantiles=(0.1, 0.3),
        config=GateConfig(trial_budget=24),
        purged_folds=3,
    )
    rows = {t.strategy_name: t.purged_diagnostic for t in exp.trials}
    assert calls == {"alpha4": 12, "high": 24}
    assert rows["xs_alpha4"].status == ("unsupported" if unsafe_alpha4 else "measured")
    assert (
        rows["xs_alpha9"].status
        == rows["xs_52w_high"].status
        == ("measured" if unsafe_alpha4 else "unsupported")
    )
    if unsafe_alpha4:
        assert rows["xs_alpha4"].reason == "unsupported_numpy_version"
    else:
        assert rows["xs_alpha4"].method == purged.ALPHA4_PURGED_METHOD
    store = JsonFileCrossSectionalStore(tmp_path / "pool.json")
    store.add(exp)
    assert store.all()[0] == exp
    view = _view(exp)
    assert CrossSectionalView.model_validate_json(view.model_dump_json()) == view


@given(window=st.sampled_from([5, 9, 21]), quantile=st.sampled_from([0.1, 0.2, 0.3]))
def test_alpha4_operative_hull_ties_warmup_oracle_and_embargo(window: int, quantile: float) -> None:
    t = window + 5
    p = pd.DataFrame(
        {"A": np.full(t + 5, 110.0), "B": np.full(t + 5, 110.0), "C": np.full(t + 5, 90.0)}
    )
    p.loc[t - window, "B"] = 90.0
    p.loc[t - 1, :] = 100.0
    p.loc[t, :] = [99.0, 100.0, 101.0]

    def calc(prices: pd.DataFrame) -> tuple[Any, ...]:
        s = alpha4_signal(prices, window)
        w = long_short_weights(s, quantile)
        gross = (w.shift(1).fillna(0) * asset_returns(prices)).sum(axis=1)
        cost = w.diff().abs().fillna(w.abs()).sum(axis=1) * 0.001
        net = portfolio_returns(s, prices, quantile=quantile)
        pd.testing.assert_series_equal(net, gross - cost, check_exact=True)
        return s, w, gross, cost, net

    base = calc(p)
    old = p.copy()
    old.loc[t - window, "A"] = 90.0
    changed = calc(old)
    assert not base[1].iloc[t - 1].equals(changed[1].iloc[t - 1])
    pd.testing.assert_series_equal(base[1].iloc[t], changed[1].iloc[t], check_exact=True)
    assert all(base[k].iloc[t] != changed[k].iloc[t] for k in (2, 3, 4))
    expired = p.copy()
    expired.iloc[: t - window] *= 3
    for a, b in zip(base, calc(expired), strict=True):
        np.testing.assert_array_equal(a.iloc[t], b.iloc[t])
    current = p.copy()
    current.loc[t, "A"] = 120.0
    cur = calc(current)
    for a, b in zip(base, cur, strict=True):
        if isinstance(a, pd.DataFrame):
            pd.testing.assert_frame_equal(a.iloc[:t], b.iloc[:t], check_exact=True)
        else:
            pd.testing.assert_series_equal(a.iloc[:t], b.iloc[:t], check_exact=True)
    assert base[2].iloc[t] != cur[2].iloc[t] and base[3].iloc[t] != cur[3].iloc[t]
    assert base[0].iloc[: window - 1].isna().all().all() and base[3].iloc[window - 1] > 0
    ties = alpha4_signal(pd.DataFrame(np.full((window + 2, 3), 100.0)), window)
    np.testing.assert_array_equal(ties.iloc[window - 1 :].to_numpy(), -1.0)
    for j in range(window - 1, len(p)):
        expected = -(
            (p.iloc[j - window + 1 : j + 1].to_numpy() <= p.iloc[j].to_numpy()).sum(axis=0) / window
        )
        np.testing.assert_array_equal(base[0].iloc[j].to_numpy(), expected)
    for stop in (window, t):
        pd.testing.assert_series_equal(
            base[4].iloc[:stop], calc(p.iloc[:stop])[4], check_exact=True
        )
    for e in (window - 1, window):
        train, test = purged_kfold_splits(120, 3, e)[1]
        left, right = int(train[train < test[0]][-1]), int(train[train > test[-1]][0])
        assert (left < int(test[0]) - window) == (e == window)
        assert (right - window > int(test[-1])) == (e == window)
