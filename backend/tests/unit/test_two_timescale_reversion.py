"""TwoTimescaleReversionStrategy (ADR-056): the level and the deviation's scale are estimated on
INDEPENDENT timescales. Every other reverting strategy in the catalog uses one window for both, and
ADR-055 measured that structure converting only 29-45% of a fast band-reversion edge whose net
oracle exceeds the AR(1) one the gate detects 22% of the time."""

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.two_timescale_reversion import TwoTimescaleReversionStrategy


def _series(values: list[float]) -> pd.Series:
    index = pd.date_range("2024-01-01", periods=len(values), freq="B", tz="UTC")
    return pd.Series(values, index=index, dtype="float64")


def _frame(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"close": close}, index=close.index)


def test_rejects_invalid_level_span() -> None:
    with pytest.raises(ValueError, match="level_span"):
        TwoTimescaleReversionStrategy(level_span=1)


def test_rejects_invalid_scale_window() -> None:
    with pytest.raises(ValueError, match="scale_window"):
        TwoTimescaleReversionStrategy(scale_window=1)


def test_rejects_invalid_k() -> None:
    with pytest.raises(ValueError, match="k"):
        TwoTimescaleReversionStrategy(k=0.0)


def test_has_real_citation() -> None:
    assert any("Avellaneda" in c for c in TwoTimescaleReversionStrategy().research_citations)


def test_parameters_round_trip() -> None:
    assert TwoTimescaleReversionStrategy(level_span=60, scale_window=10, k=2.0).parameters == {
        "level_span": 60,
        "scale_window": 10,
        "k": 2.0,
    }


def test_short_when_price_sits_above_its_slow_level() -> None:
    close = _series([100.0] * 80 + [112.0])
    signals = TwoTimescaleReversionStrategy(level_span=60, scale_window=10).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] < 0


def test_long_when_price_sits_below_its_slow_level() -> None:
    close = _series([100.0] * 80 + [88.0])
    signals = TwoTimescaleReversionStrategy(level_span=60, scale_window=10).generate_signals(
        _frame(close)
    )
    assert signals.iloc[-1] > 0


def test_the_signal_follows_the_fast_deviation_not_the_slow_level() -> None:
    """The design intent of ADR-056, on a series built to state it: a slowly drifting level with a
    fast oscillation around it. The position must track the OSCILLATION (short when rich, long when
    cheap) and must not settle into a permanent short just because the level is rising."""
    n = 400
    level = np.array([100.0 * (1.0002**i) for i in range(n)])  # ~5%/yr, a real drift
    deviation = 2.0 * np.sin(np.arange(n) * 2.0 * np.pi / 8.0)
    signals = TwoTimescaleReversionStrategy(level_span=40, scale_window=8).generate_signals(
        _frame(_series(list(level + deviation)))
    )

    settled = signals.to_numpy()[100:]
    assert np.corrcoef(settled, deviation[100:])[0, 1] < -0.5
    assert abs(settled.mean()) < 0.35


def test_a_longer_level_span_lags_a_drifting_level_and_leaves_a_larger_residual() -> None:
    """The trade-off the two parameters exist to explore, and the reason they cannot be one
    parameter: a short span tracks the level but absorbs the deviation, a long one isolates the
    deviation but carries the level's drift into it."""
    drifting = _series([100.0 * (1.0015**i) for i in range(300)])
    responsive = TwoTimescaleReversionStrategy(level_span=10, scale_window=10)
    patient = TwoTimescaleReversionStrategy(level_span=150, scale_window=10)

    close = drifting
    tight_residual = abs(close - close.ewm(span=10, adjust=False).mean()).iloc[-1]
    slow_residual = abs(close - close.ewm(span=150, adjust=False).mean()).iloc[-1]
    assert tight_residual < slow_residual
    assert responsive.parameters["level_span"] < patient.parameters["level_span"]


def test_the_scale_window_is_independent_of_the_level_span() -> None:
    """The structural claim of ADR-056. Changing only the scale window must change the signal —
    if it could not, the strategy would be a one-window z-score with extra parameters."""
    rng = np.random.default_rng(3)
    close = _series(list(100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, 300))))
    tight = TwoTimescaleReversionStrategy(level_span=60, scale_window=5).generate_signals(
        _frame(close)
    )
    loose = TwoTimescaleReversionStrategy(level_span=60, scale_window=40).generate_signals(
        _frame(close)
    )
    assert not tight.equals(loose)


def test_no_look_ahead_a_future_bar_cannot_change_an_earlier_signal() -> None:
    rng = np.random.default_rng(7)
    close = _series(list(100.0 * np.cumprod(1.0 + rng.normal(0.0, 0.01, 200))))
    strategy = TwoTimescaleReversionStrategy(level_span=60, scale_window=10)
    full = strategy.generate_signals(_frame(close))
    truncated = strategy.generate_signals(_frame(close.iloc[:-20]))
    pd.testing.assert_series_equal(full.iloc[:-20], truncated, check_freq=False)


@given(
    returns=st.lists(
        st.floats(min_value=-0.2, max_value=0.2, allow_nan=False, allow_infinity=False),
        min_size=5,
        max_size=200,
    ),
    level_span=st.integers(min_value=2, max_value=100),
    scale_window=st.integers(min_value=2, max_value=60),
)
def test_signals_are_always_a_valid_position(
    returns: list[float], level_span: int, scale_window: int
) -> None:
    """ARCHITECTURE §8: signals in [-1, 1], finite, and never NaN — including on the warm-up bars
    where neither estimator has enough history."""
    price = 100.0
    closes = []
    for r in returns:
        price *= 1 + r
        closes.append(price)
    signals = TwoTimescaleReversionStrategy(
        level_span=level_span, scale_window=scale_window
    ).generate_signals(_frame(_series(closes)))

    values = signals.to_numpy()
    assert np.isfinite(values).all()
    assert ((values >= -1.0) & (values <= 1.0)).all()


def test_a_flat_price_has_no_deviation_to_trade() -> None:
    """A zero-variance residual must be flat, not a division by zero."""
    signals = TwoTimescaleReversionStrategy().generate_signals(_frame(_series([100.0] * 120)))
    assert (signals == 0.0).all()


def test_the_catalog_offers_it_so_the_hunt_can_search_it() -> None:
    """ADR-056 is a claim about the CATALOG, not about a file. A strategy the search never
    reaches cannot move the band-reversion capture number it was written to move."""
    from app.research.strategies.catalog import STRATEGY_CATALOG

    entry = next(e for e in STRATEGY_CATALOG if e.name == "two_timescale_reversion")
    assert entry.category == "Mean Reversion"
    assert {p.name for p in entry.parameters} == {"level_span", "scale_window", "k"}


def test_the_builder_constructs_it_from_the_catalog_slug() -> None:
    from app.research.strategies.builder import build_strategy_from_dict

    strategy = build_strategy_from_dict(
        "two_timescale_reversion", {"level_span": 80, "scale_window": 12, "k": 1.5}
    )
    assert isinstance(strategy, TwoTimescaleReversionStrategy)
    assert strategy.parameters == {"level_span": 80, "scale_window": 12, "k": 1.5}


def test_the_generated_grid_separates_the_two_timescales() -> None:
    """The grid is derived mechanically from the catalog bounds (ADR-010). If those bounds made
    every generated config use one window for both jobs, the search would never test ADR-056's
    structural claim even though the strategy exists."""
    from app.research.strategies.catalog import STRATEGY_CATALOG
    from app.research.strategies.grid_generator import grid_from_catalog

    entry = next(e for e in STRATEGY_CATALOG if e.name == "two_timescale_reversion")
    grid = grid_from_catalog(entry, n_per_param=3)
    assert len(grid) >= 6
    spans = {s.parameters["level_span"] for s in grid}
    scales = {s.parameters["scale_window"] for s in grid}
    assert len(spans) >= 3 and len(scales) >= 3
    assert any(
        s.parameters["scale_window"] < s.parameters["level_span"]  # type: ignore[operator]
        for s in grid
    )
