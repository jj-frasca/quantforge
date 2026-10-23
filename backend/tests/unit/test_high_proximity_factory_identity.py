"""ADR-346: stable recognition must preserve the shipped lazy factory behavior."""

from typing import cast

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.research.cross_sectional import registry
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.purged import support_lag
from app.research.cross_sectional.strategies import high_proximity_signal


def panel() -> pd.DataFrame:
    t = np.arange(300, dtype=float)
    return pd.DataFrame({str(j): 100 + t / 9 + np.sin(t / (j + 3) + j) for j in range(6)})


def test_high_proximity_factory_has_stable_shipped_identity() -> None:
    first = registry.default_strategies()["xs_52w_high"]
    second = registry.default_strategies()["xs_52w_high"]
    assert first.build is second.build
    assert first.build is registry.high_proximity_factory
    assert first.param_grid == tuple({"window": w} for w in (126, 189, 252))


@pytest.mark.parametrize("window", [126, 189, 252, 3.9, True, np.int64(126)])
@pytest.mark.parametrize("quantile", [0.1, 0.2, 0.3])
def test_high_proximity_factory_preserves_old_signal_and_portfolio(
    window: object, quantile: float
) -> None:
    prices = panel()
    params = {"window": window}
    old_factory = lambda p: lambda data: high_proximity_signal(data, int(p["window"]))  # noqa: E731
    actual = registry.default_strategies()["xs_52w_high"].build(cast(registry.Params, params))(
        prices
    )
    expected = old_factory(params)(prices)
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=quantile),
        portfolio_returns(expected, prices, quantile=quantile),
        check_exact=True,
    )


def test_high_proximity_factory_preserves_lazy_lookup_and_mutable_mapping_capture() -> None:
    params: registry.Params = {}
    signal = registry.default_strategies()["xs_52w_high"].build(params)
    with pytest.raises(KeyError, match="window"):
        signal(panel())
    params["window"] = 126
    pd.testing.assert_frame_equal(signal(panel()), high_proximity_signal(panel(), 126))
    params["window"] = 189
    pd.testing.assert_frame_equal(signal(panel()), high_proximity_signal(panel(), 189))


def test_high_proximity_factory_does_not_enable_unaudited_purged_support(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = registry.default_strategies()["xs_52w_high"]
    configs = [(params, 0.2) for params in strategy.param_grid]
    # ADR-348 supersedes blanket deferral only for the separately audited domain.
    monkeypatch.setattr(pd, "__version__", "unaudited")
    assert support_lag(strategy, configs, panel()) == (None, "unsupported_pandas_version")


@given(window=st.integers(2, 30), scale=st.floats(0.1, 100.0))
@settings(max_examples=25)
def test_high_proximity_factory_keeps_causal_prefix_and_price_scale_invariance(
    window: int, scale: float
) -> None:
    prices = panel().iloc[:60]
    factory = registry.default_strategies()["xs_52w_high"].build({"window": window})
    signals = factory(prices)
    pd.testing.assert_frame_equal(factory(prices.iloc[:45]), signals.iloc[:45], check_exact=True)
    np.testing.assert_allclose(factory(prices * scale), signals, rtol=3e-15, atol=0, equal_nan=True)
