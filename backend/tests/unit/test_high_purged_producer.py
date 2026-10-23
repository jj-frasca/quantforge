"""ADR-348 audited runtime support; engine changes use fake receipts, never Numba."""

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional import purged, search
from app.research.cross_sectional.engine import asset_returns, portfolio_returns
from app.research.cross_sectional.registry import default_strategies
from app.research.cross_sectional.strategies import high_proximity_signal
from app.research.lab.gate import GateConfig
from app.validation.purged_cv import purged_cv_evaluate, purged_kfold_splits


def panel(n: int = 900) -> pd.DataFrame:
    t = np.arange(n, dtype=float)
    return pd.DataFrame(
        {
            f"S{i}": 100 + t * (0.01 + i * 0.003) + np.sin(t * (0.17 + i * 0.013) + i)
            for i in range(6)
        },
        index=pd.date_range("2015-01-01", periods=n, freq="B", tz="UTC"),
    )


def runtime(version: str = "3.0.6", use_numba: bool | None = False) -> Any:
    # getattr makes missing production types an assertion failure, not import error.
    cls = getattr(purged, "HighRuntime", None)
    assert cls is not None, "missing immutable high matrix runtime receipt"
    return cls(version=version, use_numba=use_numba)


def measure(
    window: int = 126, *, n: int = 900, floor: int = 0, receipt: Any = ...
) -> tuple[Any, Any]:
    prices = panel(n)
    strategy = default_strategies()["xs_52w_high"]
    configs = [({"window": window}, q) for q in (0.1, 0.3)]
    matrix = np.column_stack(
        [
            portfolio_returns(strategy.build(p)(prices), prices, quantile=q).to_numpy()
            for p, q in configs
        ]
    )
    kwargs = {} if receipt is ... else {"high_runtime": receipt}
    return purged.measure_family_purged(
        strategy,
        configs,
        prices,
        matrix,
        asset_returns(prices).mean(axis=1).to_numpy(),
        floor=floor,
        requested_folds=3,
        **kwargs,
    )


@pytest.mark.parametrize("window", [126, 189, 252])
def test_high_known_domain_uses_window_not_window_plus_one(window: int) -> None:
    strategy = default_strategies()["xs_52w_high"]
    assert purged.support_lag(strategy, [({"window": window}, 0.2)], panel()) == (window, None)


@pytest.mark.parametrize(
    "version,engine,reason",
    [
        ("3.0.7", False, "unsupported_pandas_version"),
        ("3.0.6", True, "unsupported_rolling_engine"),
    ],
)
def test_high_measurement_classifies_saved_runtime_not_current_options(
    version: str,
    engine: bool,
    reason: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = runtime(version, engine)
    # Construct the existing return matrix normally, then call with the saved
    # (synthetic) execution metadata; no Numba compiler/engine is invoked.
    diagnostic, result = measure(receipt=saved)
    assert diagnostic.status == "unsupported" and diagnostic.reason == reason
    assert diagnostic.method != purged.HIGH_PURGED_METHOD
    assert diagnostic.mean_oos_sharpe is None and result is None


@pytest.mark.parametrize("window", [126, 189, 252])
def test_high_measurement_pairs_exact_retained_folds_and_version(window: int) -> None:
    diagnostic, result = measure(window, receipt=runtime())
    assert diagnostic.method == purged.HIGH_PURGED_METHOD
    assert diagnostic.dependency_rule == "rolling-high-v1"
    assert diagnostic.max_price_lag == diagnostic.embargo == window
    prices = panel()
    matrix = np.column_stack(
        [
            portfolio_returns(high_proximity_signal(prices, window), prices, quantile=q).to_numpy()
            for q in (0.1, 0.3)
        ]
    )
    expected = purged_cv_evaluate(
        matrix,
        purged_kfold_splits(len(prices), 3, window),
        embargo=window,
        benchmark=asset_returns(prices).mean(axis=1).to_numpy(),
    )
    assert result == expected
    assert diagnostic.mean_oos_hold_sharpe == expected.mean_oos_hold_sharpe


def test_high_requires_receipt_and_keeps_custom_factory_precedence() -> None:
    with pytest.raises(ValueError, match="runtime receipt"):
        measure()
    strategy = default_strategies()["xs_52w_high"]
    custom = replace(strategy, build=lambda p: lambda prices: prices)
    d, result = purged.measure_family_purged(
        custom,
        [({"window": 126}, 0.1), ({"window": 126}, 0.3)],
        panel(300),
        np.zeros((300, 2)),
        np.zeros(300),
        floor=0,
        requested_folds=3,
    )
    assert d.reason == "unsupported_factory" and result is None


def test_high_saved_safe_receipt_is_not_replaced_by_later_global_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = runtime()
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late runtime read"))
    d, result = measure(receipt=saved)
    assert d.status == "measured" and result is not None


def test_high_floor_never_shrinks_and_no_fold_does_not_invent_scores() -> None:
    d, result = measure(252, n=300, floor=1000, receipt=runtime())
    assert d.status == "no_usable_folds" and d.embargo == 1000
    assert d.max_price_lag == 252 and d.kept_fold_ordinals == ()
    assert d.mean_oos_sharpe is None and result is None


def test_high_numeric_evaluator_refusal_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*args: Any, **kwargs: Any) -> Any:
        raise ValueError("actual high numerical refusal")

    monkeypatch.setattr(purged, "purged_cv_evaluate", broken)
    with pytest.raises(ValueError, match="actual high numerical refusal"):
        measure(receipt=runtime())


@pytest.mark.parametrize(
    "params", [{"window": 125}, {"window": True}, {"window": 126.0}, {"window": 126, "skip": 0}, {}]
)
def test_high_unshipped_parameters_remain_unsupported(params: dict[str, Any]) -> None:
    assert purged.support_lag(default_strategies()["xs_52w_high"], [(params, 0.2)], panel()) == (
        None,
        "unsupported_parameters",
    )


@pytest.mark.parametrize("dtype", ["float32", "Float64", "int64"])
def test_high_unaudited_price_dtype_stays_unsupported(dtype: str) -> None:
    prices = panel().astype(dtype)
    assert purged.support_lag(
        default_strategies()["xs_52w_high"], [({"window": 126}, 0.2)], prices
    ) == (
        None,
        "unsupported_price_dtype",
    )


@pytest.mark.parametrize("sequence", ["during", "across"])
def test_search_refuses_inconsistent_execution_receipts(
    sequence: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe, other = runtime(), runtime(use_numba=True)
    receipts = iter([safe, other] if sequence == "during" else [safe, safe, other, other])
    monkeypatch.setattr(search, "capture_high_runtime", lambda: next(receipts))
    with pytest.raises(ValueError, match=r"runtime.*changed|inconsistent.*runtime"):
        search.run_cross_sectional_search(
            panel(),
            ["xs_52w_high"],
            quantiles=(0.1, 0.3),
            config=GateConfig(trial_budget=6),
            purged_folds=3,
        )


def test_search_preserves_captured_domain_when_later_family_changes_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    safe, other = runtime(), runtime(use_numba=True)
    calls: list[Any] = []
    original = search._config_returns
    current = [safe]

    def returns(strategy: Any, *args: Any) -> Any:
        result = original(strategy, *args)
        if strategy.name == "xs_reversal":
            current[0] = other
        return result

    def capture() -> Any:
        calls.append(current[0])
        return current[0]

    monkeypatch.setattr(search, "_config_returns", returns)
    monkeypatch.setattr(search, "capture_high_runtime", capture)
    monkeypatch.setattr(purged, "capture_high_runtime", lambda: pytest.fail("late domain read"))
    exp = search.run_cross_sectional_search(
        panel(),
        ["xs_52w_high", "xs_reversal"],
        quantiles=(0.1, 0.3),
        config=GateConfig(trial_budget=12),
        purged_folds=3,
    )
    assert current[0] is other and calls and all(item is safe for item in calls)
    assert exp.trials[0].purged_diagnostic.method == purged.HIGH_PURGED_METHOD
    assert exp.trials[1].purged_diagnostic.method != purged.HIGH_PURGED_METHOD


def test_search_saved_unsafe_domain_cannot_become_supported_later(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    saved = runtime(use_numba=True)
    monkeypatch.setattr(search, "capture_high_runtime", lambda: saved)
    # This is metadata-injection control, not a claim that Numba executed.
    exp = search.run_cross_sectional_search(
        panel(),
        ["xs_52w_high"],
        quantiles=(0.1, 0.3),
        config=GateConfig(trial_budget=6),
        purged_folds=3,
    )
    assert exp.trials[0].purged_diagnostic.reason == "unsupported_rolling_engine"
    assert exp.trials[0].purged_cv_oos_sharpe is None


def test_capture_current_domain_and_version_first_unknown_option_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    capture = getattr(purged, "capture_high_runtime", None)
    assert capture is not None, "missing high runtime capture"
    assert capture() == runtime()
    monkeypatch.setattr(pd, "__version__", "future")
    monkeypatch.setattr(pd, "get_option", lambda name: pytest.fail("unknown-version option read"))
    assert capture() == runtime("future", None)


@given(window=st.sampled_from([126, 189, 252]), q=st.sampled_from([0.1, 0.2, 0.3]))
@settings(max_examples=9)
def test_high_oldest_endpoint_and_expired_prefix_net_locality(window: int, q: float) -> None:
    t = window + 5
    prices = pd.DataFrame(
        {"A": np.full(t + 2, 90.0), "B": np.full(t + 2, 80.0), "C": np.full(t + 2, 60.0)}
    )
    prices.loc[5, "A"] = 100
    prices.loc[7, ["B", "C"]] = 100
    prices.loc[t, ["A", "B"]] = [99, 84]
    original = portfolio_returns(high_proximity_signal(prices, window), prices, quantile=q)
    expired = prices.copy()
    expired.loc[4, "A"] = 200
    endpoint = prices.copy()
    endpoint.loc[5, "A"] = 200
    expired_net = portfolio_returns(high_proximity_signal(expired, window), expired, quantile=q)
    endpoint_net = portfolio_returns(high_proximity_signal(endpoint, window), endpoint, quantile=q)
    assert original.iloc[t] == expired_net.iloc[t]
    assert original.iloc[t] != endpoint_net.iloc[t]


@pytest.mark.parametrize(
    "windows,expected", [((126, 126), 126), ((126, 189), 189), ((189, 252), 252)]
)
def test_high_support_uses_actual_allocated_maximum(
    windows: tuple[int, int], expected: int
) -> None:
    configs = [({"window": w}, q) for w, q in zip(windows, (0.1, 0.3), strict=True)]
    assert purged.support_lag(
        default_strategies()["xs_52w_high"], configs, panel(), runtime=runtime()
    ) == (expected, None)


@pytest.mark.parametrize("window", [126, 189, 252])
def test_high_cython_window_operand_oracle_including_positive_extremes(window: int) -> None:
    n = 2 * window + 3
    pattern = np.array([np.nextafter(0.0, 1.0), 1e-150, 1.0, 1e150, np.finfo(float).max])
    values = np.resize(pattern, n)
    prices = pd.DataFrame({"A": values, "B": values[::-1]})
    expected = np.full((n, 2), np.nan)
    for i in range(window - 1, n):
        expected[i] = prices.iloc[i].to_numpy() / prices.iloc[
            i - window + 1 : i + 1
        ].to_numpy().max(axis=0)
    np.testing.assert_array_equal(high_proximity_signal(prices, window).to_numpy(), expected)


@pytest.mark.parametrize("window", [126, 189, 252])
def test_high_embargo_separates_both_inclusive_source_hull_endpoints(window: int) -> None:
    n = 4 * window + 30
    for embargo in (window - 1, window):
        train, test = purged_kfold_splits(n, 3, embargo)[1]
        left = train[train < test[0]][-1]
        right = train[train > test[-1]][0]
        left_overlap = set(range(left - window, left + 1)) & set(
            range(test[0] - window, test[0] + 1)
        )
        right_overlap = set(range(right - window, right + 1)) & set(
            range(test[-1] - window, test[-1] + 1)
        )
        assert bool(left_overlap) == bool(right_overlap) == (embargo == window - 1)


def test_high_runtime_receipt_is_frozen() -> None:
    from dataclasses import FrozenInstanceError

    saved = runtime()
    with pytest.raises(FrozenInstanceError):
        saved.use_numba = True
