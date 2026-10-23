"""ADR-354 preserves the shipped lazy decay factory without adopting PCV support."""

from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional import purged, registry
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.strategies import decay_reversal_signal


def panel(n: int = 70) -> pd.DataFrame:
    t = np.arange(n, dtype=float)
    return pd.DataFrame({str(i): 100 + t / 5 + np.sin(t / (i + 2) + i) for i in range(6)})


def old_factory(p: Any) -> registry.SignalFn:
    return lambda prices: decay_reversal_signal(prices, int(p["window"]))


def test_decay_stable_identity_and_original_grid() -> None:
    a, b = registry.default_strategies(), registry.default_strategies()
    assert a["xs_decay_reversal"].build is b["xs_decay_reversal"].build
    assert a["xs_decay_reversal"].build is getattr(registry, "decay_reversal_factory", None)
    assert a["xs_decay_reversal"].param_grid == tuple({"window": w} for w in (3, 5, 10))


@pytest.mark.parametrize(
    "window", [3, 5, 10, True, 5.9, np.int64(5), np.float64(3.9), "10", Decimal("5.9")]
)
@pytest.mark.parametrize("quantile", [0.1, 0.2, 0.3])
def test_decay_native_coercion_exact_outputs(window: Any, quantile: float) -> None:
    prices = panel()
    actual = registry.default_strategies()["xs_decay_reversal"].build({"window": window})(prices)
    expected = old_factory({"window": window})(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=quantile),
        portfolio_returns(expected, prices, quantile=quantile),
        check_exact=True,
    )


def test_decay_lazy_lookup_mutation_and_deletion() -> None:
    params: registry.Params = {}
    signal = registry.default_strategies()["xs_decay_reversal"].build(params)
    with pytest.raises(KeyError, match="window"):
        signal(panel())
    for window in (3, 10):
        params["window"] = window
        pd.testing.assert_frame_equal(
            signal(panel()), decay_reversal_signal(panel(), window), check_exact=True
        )
    del params["window"]
    with pytest.raises(KeyError, match="window"):
        signal(panel())


def test_decay_custom_int_timing_calls_and_native_error() -> None:
    class ChangingInt:
        calls = 0

        def __int__(self) -> int:
            self.calls += 1
            if self.calls == 3:
                raise RuntimeError("native custom conversion")
            return 3 if self.calls == 1 else 10

    value = ChangingInt()
    signal = registry.default_strategies()["xs_decay_reversal"].build({"window": value})  # type: ignore[dict-item]
    assert value.calls == 0
    for calls, window in ((1, 3), (2, 10)):
        pd.testing.assert_frame_equal(
            signal(panel()), decay_reversal_signal(panel(), window), check_exact=True
        )
        assert value.calls == calls
    with pytest.raises(RuntimeError, match="native custom conversion"):
        signal(panel())
    assert value.calls == 3


def test_decay_mapping_lookup_is_delayed_and_repeated() -> None:
    class CountingParams(dict[str, int | float]):
        calls = 0

        def __getitem__(self, key: str) -> int:
            self.calls += 1
            if self.calls == 3:
                raise RuntimeError("native mapping lookup")
            return 3 if self.calls == 1 else 10

    params = CountingParams()
    signal = registry.default_strategies()["xs_decay_reversal"].build(params)
    assert params.calls == 0
    for calls, window in ((1, 3), (2, 10)):
        pd.testing.assert_frame_equal(
            signal(panel()), decay_reversal_signal(panel(), window), check_exact=True
        )
        assert params.calls == calls
    with pytest.raises(RuntimeError, match="native mapping lookup"):
        signal(panel())


def test_decay_signal_global_is_resolved_at_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    signal = registry.default_strategies()["xs_decay_reversal"].build({"window": 3})
    prices = panel()
    calls: list[tuple[pd.DataFrame, int]] = []

    def replacement(source: pd.DataFrame, window: int) -> pd.DataFrame:
        calls.append((source, window))
        return source

    monkeypatch.setattr(registry, "decay_reversal_signal", replacement)
    assert signal(prices) is prices
    assert len(calls) == 1 and calls[0][0] is prices and calls[0][1] == 3


@pytest.mark.parametrize("window", [None, "bad", object(), float("inf"), float("nan"), -1])
def test_decay_native_error_type_message_and_timing(window: Any) -> None:
    errors = []
    for factory in (old_factory, registry.default_strategies()["xs_decay_reversal"].build):
        signal = factory({"window": window})
        with pytest.raises(Exception) as error:
            signal(panel())
        errors.append((type(error.value), str(error.value)))
    assert errors[0] == errors[1]


@pytest.mark.parametrize("window", [3, 5, 10])
def test_decay_warmup_first_entry_and_constant_ties(window: int) -> None:
    prices = panel()
    signal = registry.default_strategies()["xs_decay_reversal"].build({"window": window})(prices)
    assert signal.iloc[:window].isna().all().all()
    assert signal.iloc[window].notna().all()
    net = portfolio_returns(signal, prices)
    assert (net.iloc[:window] == 0).all() and net.iloc[window] < 0
    ties = pd.DataFrame(np.full((window + 2, 3), 100.0))
    actual = registry.default_strategies()["xs_decay_reversal"].build({"window": window})(ties)
    np.testing.assert_array_equal(actual.iloc[window:].to_numpy(), 0.0)


@pytest.mark.parametrize("window", [0, 1, 3, 10, 99])
@pytest.mark.parametrize("n", [0, 1, 4, 70])
def test_decay_tiny_empty_and_long_window_compatibility(window: int, n: int) -> None:
    prices = panel(n)
    actual = registry.default_strategies()["xs_decay_reversal"].build({"window": window})(prices)
    expected = old_factory({"window": window})(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices), portfolio_returns(expected, prices), check_exact=True
    )


def test_decay_actual_purged_producer_stays_unsupported() -> None:
    strategy = registry.default_strategies()["xs_decay_reversal"]
    prices = panel()
    configs = [({"window": 3}, 0.1), ({"window": 10}, 0.3)]
    assert purged.support_lag(strategy, configs, prices) == (None, "unsupported_factory")
    evidence, result = purged.measure_family_purged(
        strategy,
        configs,
        prices,
        np.zeros((len(prices), 2)),
        np.zeros(len(prices)),
        floor=0,
        requested_folds=3,
    )
    assert evidence.status == "unsupported" and evidence.reason == "unsupported_factory"
    assert evidence.max_price_lag is None and evidence.mean_oos_sharpe is None and result is None


@given(window=st.integers(min_value=1, max_value=25), quantile=st.sampled_from([0.1, 0.2, 0.3]))
@settings(max_examples=20, deadline=None)
def test_decay_bounded_signal_and_financial_compatibility(window: int, quantile: float) -> None:
    prices = panel()
    actual = registry.default_strategies()["xs_decay_reversal"].build({"window": window})(prices)
    expected = old_factory({"window": window})(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=quantile),
        portfolio_returns(expected, prices, quantile=quantile),
        check_exact=True,
    )
