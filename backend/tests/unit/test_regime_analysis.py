"""RegimeAnalyzer: bull/bear regimes separate and partition every bar; an all-bull market yields only the bull regime."""

from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame
from app.validation.regime_analysis import analyze_regimes


def test_regimes_separate_bull_and_bear_and_partition_the_series() -> None:
    frame = bars_to_frame(builders.regime_shift_series())
    market = frame["close"]
    strategy_returns = market.pct_change().fillna(0.0)  # buy-and-hold proxy

    regimes = analyze_regimes(strategy_returns, market, window=20)

    assert "bull" in regimes
    assert "bear" in regimes
    # the crash drags the bear-regime return negative
    assert regimes["bear"].total_return < 0.0
    # regimes partition every bar exactly once
    assert sum(m.n_bars for m in regimes.values()) == len(frame)


def test_all_bull_market_has_only_bull_regime() -> None:
    frame = bars_to_frame(builders.clean_series(n=60))  # monotonic uptrend
    market = frame["close"]
    regimes = analyze_regimes(market.pct_change().fillna(0.0), market, window=10)
    assert set(regimes) == {"bull"}
    assert regimes["bull"].n_bars == len(frame)
