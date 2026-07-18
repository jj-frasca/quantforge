from typing import Literal

from pydantic import BaseModel, ConfigDict

ParamType = Literal["int", "float"]


class ParamSchema(BaseModel):
    """One tunable parameter of a strategy — type, default, range, and human-readable copy.

    Notes:
        `name` must match the corresponding Pydantic config field on the
        BacktestRequest's discriminated `StrategyConfig`. A consistency unit test
        enforces this — adding a parameter to one side without the other is a CI fail.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    type: ParamType
    default: float
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    label: str
    description: str | None = None


StrategyCategory = Literal[
    "Trend",
    "Mean Reversion",
    "Breakout",
    "Combination",
]


class StrategySchema(BaseModel):
    """Catalog entry for one strategy — UI label, description, citations, and params.

    Notes:
        `name` is the discriminator value used on POST /backtest (and is the
        backend's strategy slug, not the algorithm's full name like "sma_crossover").
        `category` groups strategies in the frontend dropdown via <optgroup> — a flat
        list got noisy past ~8 entries; categorization restores quick navigation
        without inventing taxonomy beyond what every quant reader already knows.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    label: str
    category: StrategyCategory
    # One plain-English sentence: what the strategy DOES, in language a non-quant can
    # parse on first read. Distinct from `description` (which goes into the implementation
    # nuance). This is the strategy's user-facing face.
    summary: str
    description: str
    citations: list[str]
    parameters: list[ParamSchema]


# Source of truth for what's available + how to render the form. Adding a strategy =
# (1) new Pydantic config variant in the StrategyConfig union (app/api/v1/backtest.py),
# (2) new BaseStrategy subclass under app/research/strategies/,
# (3) new entry here. The consistency test keeps (1) and (3) in sync.
STRATEGY_CATALOG: list[StrategySchema] = [
    StrategySchema(
        name="sma",
        label="SMA Crossover",
        category="Trend",
        summary="Buys when the recent average price has been rising; sells when it has been falling.",
        description=(
            "Long when the fast moving average crosses above the slow; short when below. "
            "Trailing windows mean no look-ahead. Classic trend-following baseline."
        ),
        citations=["Simple moving-average crossover (textbook); no external citation required."],
        parameters=[
            ParamSchema(
                name="fast",
                type="int",
                default=20,
                minimum=1,
                maximum=200,
                label="Fast window",
                description="Bars in the fast (short) moving average",
            ),
            ParamSchema(
                name="slow",
                type="int",
                default=50,
                minimum=2,
                maximum=500,
                label="Slow window",
                description="Bars in the slow (long) moving average; must be > fast",
            ),
        ],
    ),
    StrategySchema(
        name="momentum",
        label="Time-Series Momentum",
        category="Trend",
        summary="Buys what has been going up over the past few months; sells what has been going down.",
        description=(
            "Long past winners, short past losers — sign of the trailing return over "
            "`lookback` bars, ending `skip` bars ago (the skip avoids short-term reversal)."
        ),
        citations=["Jegadeesh & Titman (1993), Journal of Finance 48(1), pp. 65-91."],
        parameters=[
            ParamSchema(
                name="lookback",
                type="int",
                default=60,
                minimum=1,
                maximum=500,
                label="Lookback window",
                description="Bars over which the trailing return is measured",
            ),
            ParamSchema(
                name="skip",
                type="int",
                default=5,
                minimum=0,
                maximum=60,
                label="Skip bars",
                description="Recent bars dropped from the lookback to avoid mean-reversion noise",
            ),
        ],
    ),
    StrategySchema(
        name="mean_reversion",
        label="Mean Reversion (z-score)",
        category="Mean Reversion",
        summary="Bets the price will snap back toward its recent average — buys when it is unusually low, sells when unusually high.",
        description=(
            "Short when price is rich vs. its rolling mean, long when cheap. "
            "Signal = -clip(z / k, -1, 1) where z is the trailing z-score of price."
        ),
        citations=["Avellaneda & Lee (2010), Quantitative Finance 10(7), pp. 761-782."],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Window",
                description="Bars in the rolling mean and standard deviation",
            ),
            ParamSchema(
                name="k",
                type="float",
                default=2.0,
                minimum=0.1,
                maximum=10.0,
                step=0.1,
                label="k (z-score scale)",
                description="Saturation point: signal hits ±1 at |z| = k",
            ),
        ],
    ),
    StrategySchema(
        name="rsi_mean_reversion",
        label="RSI Mean Reversion",
        category="Mean Reversion",
        summary="Buys after the price has been weak for a while; sells after it has been strong — assuming both will reverse.",
        description=(
            "Long when the Relative Strength Index drops below `oversold`, short above "
            "`overbought`, flat between. Classic Wilder RSI (1978)."
        ),
        citations=[
            "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=14,
                minimum=2,
                maximum=100,
                label="RSI window",
                description="Bars used in the rolling RSI calculation",
            ),
            ParamSchema(
                name="oversold",
                type="float",
                default=30.0,
                minimum=1.0,
                maximum=49.0,
                step=1.0,
                label="Oversold threshold",
                description="Go long when RSI drops below this level",
            ),
            ParamSchema(
                name="overbought",
                type="float",
                default=70.0,
                minimum=51.0,
                maximum=99.0,
                step=1.0,
                label="Overbought threshold",
                description="Go short when RSI rises above this level",
            ),
        ],
    ),
    StrategySchema(
        name="donchian_breakout",
        label="Donchian Channel Breakout",
        category="Breakout",
        summary="Waits for the price to break above a recent high (long) or below a recent low (short), then rides the move.",
        description=(
            "Long when the close breaks above the prior `lookback`-bar high; short "
            "when it breaks below the prior low. Carries the last breakout forward "
            "(Turtle Trader rule)."
        ),
        citations=["Faith, Curtis M. Way of the Turtle. McGraw-Hill, 2007."],
        parameters=[
            ParamSchema(
                name="lookback",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Channel lookback",
                description="Bars in the rolling high/low channel that defines a breakout",
            ),
        ],
    ),
    StrategySchema(
        name="bollinger_bands",
        label="Bollinger Bands Mean Reversion",
        category="Mean Reversion",
        summary="Bets on snap-back to the average, using volatility-scaled bands to decide when the price has wandered 'far enough'.",
        description=(
            "Long when the close drops below the lower band (mean - num_std * sigma); "
            "short when it rises above the upper band. Flat between the bands. Discrete "
            "signal -- cousin to the continuous z-score mean reversion."
        ),
        citations=["Bollinger, John. Bollinger on Bollinger Bands. McGraw-Hill, 2001."],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Window",
                description="Bars in the rolling mean / std that define the bands",
            ),
            ParamSchema(
                name="num_std",
                type="float",
                default=2.0,
                minimum=0.5,
                maximum=5.0,
                step=0.1,
                label="Band width (sigma)",
                description="Number of standard deviations the bands sit from the mean",
            ),
        ],
    ),
    StrategySchema(
        name="macd_crossover",
        label="MACD Crossover",
        category="Trend",
        summary="Same idea as SMA crossover, but smoother and faster to react when the trend turns.",
        description=(
            "Long when the MACD line (EMA fast - EMA slow) is above its signal line "
            "(EMA of MACD); short when below. Conventional 12/26/9 trend-following filter."
        ),
        citations=[
            "Appel, Gerald. Technical Analysis: Power Tools for Active Investors. FT Press, 2005."
        ],
        parameters=[
            ParamSchema(
                name="fast",
                type="int",
                default=12,
                minimum=1,
                maximum=200,
                label="Fast EMA span",
                description="Span of the fast exponential moving average",
            ),
            ParamSchema(
                name="slow",
                type="int",
                default=26,
                minimum=2,
                maximum=500,
                label="Slow EMA span",
                description="Span of the slow EMA; must be > fast",
            ),
            ParamSchema(
                name="signal",
                type="int",
                default=9,
                minimum=1,
                maximum=100,
                label="Signal EMA span",
                description="Span of the EMA applied to the MACD line",
            ),
        ],
    ),
    StrategySchema(
        name="keltner_channel",
        label="Keltner Channel Breakout",
        category="Breakout",
        summary="Like Donchian breakout, but the bands widen with volatility — fewer false signals in choppy markets.",
        description=(
            "Volatility-adaptive channel: midline = EMA(close), width = multiplier * ATR. "
            "Long when the close breaks above the upper band, short below the lower, flat "
            "between. Channels widen in choppy regimes (fewer false breakouts than Donchian)."
        ),
        citations=[
            "Keltner, Chester W. How To Make Money in Commodities. Keltner Statistical Service, 1960.",
            "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978.",
        ],
        parameters=[
            ParamSchema(
                name="ma_window",
                type="int",
                default=20,
                minimum=1,
                maximum=200,
                label="Midline EMA span",
                description="Span of the EMA that forms the channel midline",
            ),
            ParamSchema(
                name="atr_window",
                type="int",
                default=14,
                minimum=2,
                maximum=100,
                label="ATR window",
                description="Bars in the rolling Average True Range",
            ),
            ParamSchema(
                name="multiplier",
                type="float",
                default=2.0,
                minimum=0.5,
                maximum=5.0,
                step=0.1,
                label="Band width (ATR multiple)",
                description="How many ATRs the bands sit from the midline",
            ),
        ],
    ),
    StrategySchema(
        name="vol_targeted_sma",
        label="Vol-Targeted SMA Crossover",
        category="Trend",
        summary="An SMA crossover that shrinks the position size in choppy markets — same direction, less white-knuckle ride.",
        description=(
            "Same fast/slow SMA crossover as the basic SMA strategy, but the position "
            "size is scaled by `target_vol / realized_vol` (clipped to <= 1, no leverage). "
            "Demonstrates risk management on top of signal generation: shrinks position "
            "in choppy regimes so portfolio volatility stays approximately constant."
        ),
        citations=[
            "Moskowitz, Ooi & Pedersen (2012), 'Time Series Momentum'. "
            "Journal of Financial Economics 104(2), pp. 228-250."
        ],
        parameters=[
            ParamSchema(
                name="fast",
                type="int",
                default=20,
                minimum=1,
                maximum=200,
                label="Fast SMA window",
                description="Bars in the fast moving average",
            ),
            ParamSchema(
                name="slow",
                type="int",
                default=50,
                minimum=2,
                maximum=500,
                label="Slow SMA window",
                description="Bars in the slow moving average; must be > fast",
            ),
            ParamSchema(
                name="vol_window",
                type="int",
                default=30,
                minimum=2,
                maximum=252,
                label="Vol-estimation window",
                description="Bars in the rolling std used to estimate realized volatility",
            ),
            ParamSchema(
                name="target_vol",
                type="float",
                default=0.15,
                minimum=0.01,
                maximum=1.0,
                step=0.01,
                label="Target annualized vol",
                description="Portfolio vol target (e.g. 0.15 = 15% annualized)",
            ),
        ],
    ),
    StrategySchema(
        name="trend_filtered_mean_reversion",
        label="Trend-Filtered Mean Reversion",
        category="Combination",
        summary="Only buys oversold dips when the longer trend is up, and only shorts overbought spikes when the longer trend is down. Avoids the falling-knife trap.",
        description=(
            "Mean-reversion bets gated by the longer trend: long oversold (z < -threshold) "
            "ONLY inside an uptrend; short overbought ONLY inside a downtrend. Avoids "
            "the classic 'falling knife' failure mode of blind mean reversion."
        ),
        citations=[
            "Connors, Larry & Alvarez, Cesar. Short Term Trading Strategies That Work. "
            "TradingMarkets Publishing Group, 2009."
        ],
        parameters=[
            ParamSchema(
                name="z_window",
                type="int",
                default=20,
                minimum=2,
                maximum=100,
                label="Z-score window",
                description="Bars in the rolling mean / std for the short-term z-score",
            ),
            ParamSchema(
                name="z_threshold",
                type="float",
                default=1.5,
                minimum=0.5,
                maximum=4.0,
                step=0.1,
                label="Z-score threshold",
                description="How far from the rolling mean to call oversold / overbought",
            ),
            ParamSchema(
                name="trend_window",
                type="int",
                default=100,
                minimum=20,
                maximum=400,
                label="Trend SMA window",
                description="Bars in the longer-term trend filter (must be > z_window)",
            ),
        ],
    ),
    StrategySchema(
        name="triple_ma_alignment",
        label="Triple MA Alignment",
        category="Trend",
        summary="Long only when three different averages agree the trend is up; short only when they agree it is down; stays flat the rest of the time.",
        description=(
            "Three SMAs at three windows must agree on direction: long when fast > "
            "medium > slow; short when fast < medium < slow; flat otherwise. Stricter "
            "than a two-MA crossover -- fewer trades, longer holds, no fighting the chop."
        ),
        citations=["Elder, Alexander. Trading for a Living. Wiley, 1993."],
        parameters=[
            ParamSchema(
                name="fast",
                type="int",
                default=10,
                minimum=1,
                maximum=100,
                label="Fast window",
                description="Bars in the fastest SMA",
            ),
            ParamSchema(
                name="medium",
                type="int",
                default=30,
                minimum=2,
                maximum=200,
                label="Medium window",
                description="Bars in the middle SMA; must be > fast",
            ),
            ParamSchema(
                name="slow",
                type="int",
                default=100,
                minimum=3,
                maximum=400,
                label="Slow window",
                description="Bars in the slowest SMA; must be > medium",
            ),
        ],
    ),
    StrategySchema(
        name="williams_r",
        label="Williams %R",
        category="Mean Reversion",
        summary="Buys when the price is stuck near its recent lows and sells when it is near its recent highs, betting on a bounce.",
        description=(
            "Williams %R oscillator: long when %R falls below the oversold level (close "
            "pinned near the window low), short when it rises above overbought (near the "
            "window high), flat between. Trailing high/low windows -- no look-ahead."
        ),
        citations=[
            "Williams, Larry. How I Made One Million Dollars Last Year Trading Commodities. "
            "Windsor Books, 1979."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=14,
                minimum=2,
                maximum=200,
                label="Lookback window",
                description="Bars in the rolling high/low that define the %R range",
            ),
            ParamSchema(
                name="oversold",
                type="float",
                default=-80.0,
                minimum=-99.0,
                maximum=-51.0,
                step=1.0,
                label="Oversold threshold",
                description="Go long when %R drops below this level (range -100..0)",
            ),
            ParamSchema(
                name="overbought",
                type="float",
                default=-20.0,
                minimum=-49.0,
                maximum=-1.0,
                step=1.0,
                label="Overbought threshold",
                description="Go short when %R rises above this level; must be > oversold",
            ),
        ],
    ),
    StrategySchema(
        name="cci",
        label="Commodity Channel Index",
        category="Mean Reversion",
        summary="Measures how far the price has strayed from its recent average and bets it will snap back.",
        description=(
            "CCI = (typical price - SMA) / (0.015 * mean abs deviation). Long when CCI "
            "drops below -threshold (oversold), short above +threshold (overbought), flat "
            "between. Trailing rolling stats -- no look-ahead."
        ),
        citations=["Lambert, Donald R. 'Commodity Channel Index'. Commodities magazine, 1980."],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Window",
                description="Bars in the rolling mean and mean-absolute-deviation",
            ),
            ParamSchema(
                name="threshold",
                type="float",
                default=100.0,
                minimum=50.0,
                maximum=300.0,
                step=5.0,
                label="CCI threshold",
                description="Absolute CCI level that triggers a long (below -threshold) or short",
            ),
        ],
    ),
    StrategySchema(
        name="stochastic_oscillator",
        label="Stochastic Oscillator",
        category="Mean Reversion",
        summary="Tracks where the close sits inside its recent range and fades the extremes -- buy near the bottom, sell near the top.",
        description=(
            "Smoothed stochastic: %K = position of the close within the window high/low "
            "range, %D = SMA of %K. Long when %D is below the oversold level, short above "
            "overbought, flat between. Trailing windows -- no look-ahead."
        ),
        citations=[
            "Lane, George C. 'Lane's Stochastics'. Technical Analysis of Stocks & Commodities, 1984."
        ],
        parameters=[
            ParamSchema(
                name="k_window",
                type="int",
                default=14,
                minimum=2,
                maximum=200,
                label="%K window",
                description="Bars in the rolling high/low range for the raw %K",
            ),
            ParamSchema(
                name="d_window",
                type="int",
                default=3,
                minimum=1,
                maximum=50,
                label="%D smoothing",
                description="Bars in the SMA that smooths %K into the traded %D line",
            ),
            ParamSchema(
                name="oversold",
                type="float",
                default=20.0,
                minimum=1.0,
                maximum=49.0,
                step=1.0,
                label="Oversold threshold",
                description="Go long when %D drops below this level",
            ),
            ParamSchema(
                name="overbought",
                type="float",
                default=80.0,
                minimum=51.0,
                maximum=99.0,
                step=1.0,
                label="Overbought threshold",
                description="Go short when %D rises above this level; must be > oversold",
            ),
        ],
    ),
    StrategySchema(
        name="trix",
        label="TRIX",
        category="Trend",
        summary="Follows a heavily smoothed trend, going long when it turns up and short when it turns down.",
        description=(
            "Triple-smoothed EMA of the close (three chained EMAs of span `window`), then the "
            "bar-over-bar percent change (TRIX), smoothed again over `signal`. Long when the "
            "smoothed TRIX is positive, short when negative, flat at zero. Recursive EMAs + "
            "trailing pct_change -- no look-ahead."
        ),
        citations=[
            "Hutson, Jack K. 'Good TRIX'. Technical Analysis of Stocks & Commodities 1, "
            "no. 5 (1983)."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=15,
                minimum=2,
                maximum=200,
                label="EMA window",
                description="Span of each of the three chained EMAs that smooth the close",
            ),
            ParamSchema(
                name="signal",
                type="int",
                default=9,
                minimum=1,
                maximum=100,
                label="Signal smoothing",
                description="Span of the EMA that smooths TRIX before the zero-line comparison",
            ),
        ],
    ),
    StrategySchema(
        name="aroon",
        label="Aroon",
        category="Trend",
        summary="Follows the trend by asking whether a new high or a new low happened more recently.",
        description=(
            "Over a trailing window, Aroon-Up measures how recently the highest high was made "
            "and Aroon-Down the lowest low. Long when Aroon-Up > Aroon-Down (highs are fresher "
            "-- up-trend), short when Aroon-Down > Aroon-Up, flat when equal. Rolling argmax/"
            "argmin -- no look-ahead."
        ),
        citations=["Chande, Tushar S. 'Aroon' (1995). Technical Analysis of Stocks & Commodities."],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=25,
                minimum=2,
                maximum=200,
                label="Lookback window",
                description="Bars in the trailing window that locates the most recent high/low",
            ),
        ],
    ),
    StrategySchema(
        name="chaikin_money_flow",
        label="Chaikin Money Flow",
        category="Trend",
        summary="Uses where each bar closes within its range, weighted by volume, to gauge buying vs selling pressure.",
        description=(
            "Money-flow multiplier = ((close - low) - (high - close)) / (high - low) per bar, "
            "volume-weighted and summed over `window` divided by summed volume = CMF in [-1, 1]. "
            "Long when CMF > threshold (net accumulation), short when CMF < -threshold "
            "(distribution), flat between. Trailing rolling sums -- no look-ahead."
        ),
        citations=[
            "Chaikin, Marc. Chaikin Money Flow (1980s); see Achelis, Technical Analysis A to Z "
            "(2000)."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Lookback window",
                description="Bars in the trailing money-flow and volume sums",
            ),
            ParamSchema(
                name="threshold",
                type="float",
                default=0.05,
                minimum=0.01,
                maximum=0.5,
                step=0.01,
                label="CMF threshold",
                description="Absolute CMF level that triggers a long (above) or short (below -threshold)",
            ),
        ],
    ),
    StrategySchema(
        name="vwap_reversion",
        label="VWAP Reversion",
        category="Mean Reversion",
        summary="Bets the price snaps back toward the volume-weighted average when it strays too far from it.",
        description=(
            "Rolling VWAP = sum(typical price x volume) / sum(volume) over `window`, typical = "
            "(high + low + close) / 3. Deviation (close - VWAP) / VWAP: long when below "
            "-threshold (cheap vs where volume traded), short when above +threshold, flat "
            "between. Trailing rolling sums -- no look-ahead."
        ),
        citations=[
            "Berkowitz, S.A., Logue, D.E., Noser, E.A. 'The Total Cost of Transactions on the "
            "NYSE'. Journal of Finance 43, no. 1 (1988)."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=20,
                minimum=2,
                maximum=200,
                label="Lookback window",
                description="Bars in the trailing VWAP (price x volume and volume sums)",
            ),
            ParamSchema(
                name="threshold",
                type="float",
                default=0.02,
                minimum=0.005,
                maximum=0.2,
                step=0.005,
                label="Deviation threshold",
                description="Fractional distance from VWAP that triggers a long (below) or short (above)",
            ),
        ],
    ),
    StrategySchema(
        name="adx",
        label="ADX Directional Movement",
        category="Trend",
        summary="Trades with the dominant trend direction, but only when the trend is strong enough to bother.",
        description=(
            "Wilder's +DI / -DI measure up vs down directional movement; ADX measures trend "
            "strength regardless of direction. Long when +DI > -DI and ADX > threshold, short "
            "when -DI > +DI and ADX > threshold, flat when the trend is weak. Wilder smoothing "
            "on shifted inputs -- no look-ahead."
        ),
        citations=[
            "Wilder, J. Welles. New Concepts in Technical Trading Systems. Trend Research, 1978."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=14,
                minimum=2,
                maximum=100,
                label="Smoothing window",
                description="Wilder smoothing period for TR, +DM/-DM, and ADX",
            ),
            ParamSchema(
                name="threshold",
                type="float",
                default=25.0,
                minimum=10.0,
                maximum=60.0,
                step=1.0,
                label="ADX trend-strength threshold",
                description="Minimum ADX to treat the trend as strong enough to trade",
            ),
        ],
    ),
    StrategySchema(
        name="connors_rsi",
        label="Connors RSI (2-period)",
        category="Mean Reversion",
        summary="Buys after a sharp short-term drop and sells after a sharp short-term pop, betting the move snaps back.",
        description=(
            "Larry Connors' short-period RSI mean reversion: a very short (default 2-bar) Wilder "
            "RSI at extreme thresholds. Long when RSI drops below `oversold` (deeply oversold), "
            "short when it rises above `overbought`, flat between. Recursive Wilder smoothing on "
            "close-to-close moves -- no look-ahead."
        ),
        citations=[
            "Connors, Larry & Alvarez, Cesar. Short Term Trading Strategies That Work. "
            "TradingMarkets Publishing Group, 2009."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=2,
                minimum=2,
                maximum=50,
                label="RSI window",
                description="Bars in the short-period Wilder RSI (Connors' default is 2)",
            ),
            ParamSchema(
                name="oversold",
                type="float",
                default=10.0,
                minimum=1.0,
                maximum=49.0,
                step=1.0,
                label="Oversold threshold",
                description="Go long when RSI drops below this level",
            ),
            ParamSchema(
                name="overbought",
                type="float",
                default=90.0,
                minimum=51.0,
                maximum=99.0,
                step=1.0,
                label="Overbought threshold",
                description="Go short when RSI rises above this level; must be > oversold",
            ),
        ],
    ),
    StrategySchema(
        name="fifty_two_week_high",
        label="52-Week High Momentum",
        category="Trend",
        summary="Buys stocks trading near their one-year high and shorts those stuck far below it.",
        description=(
            "Proximity = close / trailing-window high. Long when proximity >= near_high (at/near "
            "the high -- traders under-react to good news, per George & Hwang 2004), short when "
            "proximity <= near_low (deep below), flat in the band between. Trailing rolling max -- "
            "no look-ahead."
        ),
        citations=[
            "George, Thomas J., and Chuan-Yang Hwang. 'The 52-Week High and Momentum Investing'. "
            "Journal of Finance 59, no. 5 (2004), pp. 2145-2176."
        ],
        parameters=[
            ParamSchema(
                name="window",
                type="int",
                default=252,
                minimum=2,
                maximum=504,
                label="Lookback window",
                description="Bars in the trailing high (252 ~ one trading year)",
            ),
            ParamSchema(
                name="near_high",
                type="float",
                default=0.95,
                minimum=0.5,
                maximum=1.0,
                step=0.01,
                label="Near-high threshold",
                description="Go long when close/high is at or above this fraction",
            ),
            ParamSchema(
                name="near_low",
                type="float",
                default=0.70,
                minimum=0.1,
                maximum=0.99,
                step=0.01,
                label="Near-low threshold",
                description="Go short when close/high is at or below this fraction; must be < near_high",
            ),
        ],
    ),
    StrategySchema(
        name="ultimate_oscillator",
        label="Ultimate Oscillator",
        category="Mean Reversion",
        summary="Blends buying pressure over three timeframes to spot exhausted selling or buying, then fades it.",
        description=(
            "Larry Williams' oscillator: buying pressure / true range averaged over 7, 14, 28 bars "
            "and weighted 4:2:1 into a 0-100 line. Long when it drops below oversold (spent "
            "selling), short above overbought, flat between. The multi-timeframe blend cuts the "
            "false signals a single-window oscillator throws. Trailing sums -- no look-ahead."
        ),
        citations=[
            "Williams, Larry. 'The Ultimate Oscillator'. Technical Analysis of Stocks & "
            "Commodities (1976)."
        ],
        parameters=[
            ParamSchema(
                name="oversold",
                type="float",
                default=30.0,
                minimum=1.0,
                maximum=49.0,
                step=1.0,
                label="Oversold threshold",
                description="Go long when the oscillator drops below this level",
            ),
            ParamSchema(
                name="overbought",
                type="float",
                default=70.0,
                minimum=51.0,
                maximum=99.0,
                step=1.0,
                label="Overbought threshold",
                description="Go short when the oscillator rises above this level; must be > oversold",
            ),
        ],
    ),
    StrategySchema(
        name="vol_managed_momentum",
        label="Volatility-Managed Momentum",
        category="Trend",
        summary="Follows the trend, but cuts position size hard after markets get turbulent and leans in when they are calm.",
        description=(
            "Moreira & Muir (2017): scale a momentum sign by the inverse of recent realized "
            "VARIANCE. Direction is the sign of the trailing return over `lookback` bars; size "
            "is target_variance / realized_variance, clipped to [0, 1] (de-risk only, no "
            "leverage). Inverse-variance de-risks more aggressively after vol spikes than the "
            "inverse-vol scaling of vol-targeted SMA. Trailing log-return variance -- no look-ahead."
        ),
        citations=[
            "Moreira, Alan, and Tyler Muir. 'Volatility-Managed Portfolios'. "
            "Journal of Finance 72, no. 4 (2017), pp. 1611-1644."
        ],
        parameters=[
            ParamSchema(
                name="lookback",
                type="int",
                default=60,
                minimum=1,
                maximum=500,
                label="Momentum lookback",
                description="Bars over which the trailing return sets the trade direction",
            ),
            ParamSchema(
                name="vol_window",
                type="int",
                default=20,
                minimum=2,
                maximum=252,
                label="Variance window",
                description="Bars in the rolling realized-variance estimate that scales the position",
            ),
            ParamSchema(
                name="target_vol",
                type="float",
                default=0.15,
                minimum=0.01,
                maximum=1.0,
                step=0.01,
                label="Target annualized vol",
                description="Annualized vol target; target variance = target_vol squared",
            ),
        ],
    ),
    StrategySchema(
        name="residual_momentum",
        label="Residual Momentum",
        category="Trend",
        summary="Trend-follows the part of returns that isn't just the stock's usual drift — steadier than raw momentum.",
        description=(
            "Residual return = daily return minus its own trailing mean (the name's recent drift). "
            "Signal = sign of the summed residual over `lookback` bars ending `skip` bars ago. Long "
            "when recent returns ran above the name's own trend, short below, flat when they track "
            "it. Blitz-Huij-Martens (2011): residual momentum is less crash-prone than raw price "
            "momentum. Single-name proxy (removes own drift, not a market beta). Trailing/shifted "
            "-- no look-ahead."
        ),
        citations=[
            "Blitz, David, Joop Huij, and Martin Martens. 'Residual Momentum'. "
            "Journal of Empirical Finance 18, no. 3 (2011), pp. 506-521."
        ],
        parameters=[
            ParamSchema(
                name="lookback",
                type="int",
                default=120,
                minimum=1,
                maximum=500,
                label="Momentum lookback",
                description="Bars over which the residual return is summed",
            ),
            ParamSchema(
                name="skip",
                type="int",
                default=20,
                minimum=0,
                maximum=60,
                label="Skip bars",
                description="Recent bars dropped from the lookback to avoid short-term reversal",
            ),
            ParamSchema(
                name="mean_window",
                type="int",
                default=60,
                minimum=2,
                maximum=252,
                label="Drift window",
                description="Trailing window whose mean return is removed to form the residual",
            ),
        ],
    ),
]
