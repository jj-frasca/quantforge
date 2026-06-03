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


class StrategySchema(BaseModel):
    """Catalog entry for one strategy — UI label, description, citations, and params.

    Notes:
        `name` is the discriminator value used on POST /backtest (and is the
        backend's strategy slug, not the algorithm's full name like "sma_crossover").
    """

    model_config = ConfigDict(frozen=True)

    name: str
    label: str
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
]
