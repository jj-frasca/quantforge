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
]
