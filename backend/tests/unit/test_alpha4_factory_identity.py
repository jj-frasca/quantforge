"""ADR-351 identity-only compatibility; producer domain is governed by ADR-353."""

from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional import purged, registry
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.strategies import alpha4_signal


def panel() -> pd.DataFrame:
    t = np.arange(70, dtype=float)
    return pd.DataFrame({str(i): 100 + t / 5 + np.sin(t / (i + 2) + i) for i in range(6)})


def old_factory(p: Any) -> registry.SignalFn:
    return lambda prices: alpha4_signal(prices, int(p["window"]))


def test_alpha4_stable_identity_and_original_grid() -> None:
    a, b = registry.default_strategies(), registry.default_strategies()
    assert a["xs_alpha4"].build is b["xs_alpha4"].build
    assert a["xs_alpha4"].build is getattr(registry, "alpha4_factory", None)
    assert a["xs_alpha4"].param_grid == tuple({"window": w} for w in (5, 9, 21))


@pytest.mark.parametrize(
    "window", [5, 9, 21, True, 5.9, np.int64(9), np.float64(5.9), "9", Decimal("5.9")]
)
@pytest.mark.parametrize("quantile", [0.1, 0.2, 0.3])
def test_alpha4_native_coercion_exact_outputs(window: Any, quantile: float) -> None:
    prices = panel()
    actual = registry.default_strategies()["xs_alpha4"].build({"window": window})(prices)
    expected = old_factory({"window": window})(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=quantile),
        portfolio_returns(expected, prices, quantile=quantile),
        check_exact=True,
    )


def test_alpha4_lazy_lookup_mutation_and_deletion() -> None:
    params: registry.Params = {}
    signal = registry.default_strategies()["xs_alpha4"].build(params)
    with pytest.raises(KeyError, match="window"):
        signal(panel())
    for window in (5, 21):
        params["window"] = window
        pd.testing.assert_frame_equal(
            signal(panel()), alpha4_signal(panel(), window), check_exact=True
        )
    del params["window"]
    with pytest.raises(KeyError, match="window"):
        signal(panel())


def test_alpha4_custom_int_timing_calls_and_native_error() -> None:
    class ChangingInt:
        calls = 0

        def __int__(self) -> int:
            self.calls += 1
            if self.calls == 3:
                raise RuntimeError("native custom conversion")
            return 5 if self.calls == 1 else 9

    value = ChangingInt()
    signal = registry.default_strategies()["xs_alpha4"].build({"window": value})  # type: ignore[dict-item]
    assert value.calls == 0
    for calls, window in ((1, 5), (2, 9)):
        pd.testing.assert_frame_equal(
            signal(panel()), alpha4_signal(panel(), window), check_exact=True
        )
        assert value.calls == calls
    with pytest.raises(RuntimeError, match="native custom conversion"):
        signal(panel())
    assert value.calls == 3


@pytest.mark.parametrize("window", [None, "bad", object(), float("inf"), float("nan"), -1])
def test_alpha4_native_error_type_message_and_timing(window: Any) -> None:
    errors = []
    for factory in (old_factory, registry.default_strategies()["xs_alpha4"].build):
        signal = factory({"window": window})
        with pytest.raises(Exception) as error:
            signal(panel())
        errors.append((type(error.value), str(error.value)))
    assert errors[0] == errors[1]


@pytest.mark.parametrize("window", [5, 9, 21])
def test_alpha4_ties_and_warmup(window: int) -> None:
    prices = panel()
    signal = registry.default_strategies()["xs_alpha4"].build({"window": window})(prices)
    assert signal.iloc[: window - 1].isna().all().all()
    assert signal.iloc[window - 1].notna().all()
    net = portfolio_returns(signal, prices)
    assert (net.iloc[: window - 1] == 0).all()
    assert net.iloc[window - 1] < 0
    ties = pd.DataFrame(np.full((window + 2, 3), 100.0))
    actual = registry.default_strategies()["xs_alpha4"].build({"window": window})(ties)
    np.testing.assert_array_equal(actual.iloc[window - 1 :].to_numpy(), -1.0)


def test_alpha4_actual_purged_producer_refuses_unaudited_numpy() -> None:
    # ADR-353 supersedes the blanket refusal with a dedicated unaudited-domain check.
    receipt = purged.Alpha4Runtime("3.0.6", "unaudited", False)
    strategy = registry.default_strategies()["xs_alpha4"]
    prices = panel()
    configs: list[tuple[registry.Params, float]] = [
        ({"window": 5}, 0.1),
        ({"window": 21}, 0.3),
    ]
    assert purged.support_lag(strategy, configs, prices, alpha4_runtime=receipt) == (
        None,
        "unsupported_numpy_version",
    )
    evidence, result = purged.measure_family_purged(
        strategy,
        configs,
        prices,
        np.zeros((len(prices), 2)),
        np.zeros(len(prices)),
        floor=0,
        requested_folds=3,
        alpha4_runtime=receipt,
    )
    assert evidence.status == "unsupported" and evidence.reason == "unsupported_numpy_version"
    assert evidence.max_price_lag is None and evidence.mean_oos_sharpe is None and result is None


@given(window=st.integers(min_value=1, max_value=25), quantile=st.sampled_from([0.1, 0.2, 0.3]))
@settings(max_examples=20, deadline=None)
def test_alpha4_bounded_factory_compatibility(window: int, quantile: float) -> None:
    prices = panel()
    actual = registry.default_strategies()["xs_alpha4"].build({"window": window})(prices)
    expected = old_factory({"window": window})(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=quantile),
        portfolio_returns(expected, prices, quantile=quantile),
        check_exact=True,
    )
