from collections.abc import Mapping, Sequence
from statistics import median
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import BaseModel, ConfigDict

from app.research.lab.experiment import Experiment
from app.research.lab.gate import GateConfig
from app.research.lab.holdout import split_holdout
from app.research.lab.search import run_search
from app.research.lab.universe import expected_max_sharpe_under_null

_TRADING_DAYS = 252
_COLUMNS = ["open", "high", "low", "close", "volume"]
_START = "2010-01-04"


class NullCalibration(BaseModel):
    """The gate's measured behavior on a universe with no edge by construction (ADR-036).

    `false_graduation_rate` is a Type-I error for the WHOLE pipeline — search, DSR, PBO, MinTRL,
    holdout and beat-buy-and-hold together — which none of those components' individual guarantees
    implies. It is a property of `gate_config_version`; re-measure whenever the gate changes.
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    n_graduates: int
    false_graduation_rate: float
    n_clear_deflation_bar: int
    deflation_bar: float
    max_deflated_sharpe: float
    max_holdout_sharpe: float | None
    graduate_symbols: list[str]
    errors: dict[str, str]
    gate_config_version: str


# Widened past the repo's usual NDArray[float64]: numpy types these products as
# floating[Any], and _ohlcv only feeds them to a DataFrame constructor.
FloatArray = npt.NDArray[np.floating[Any]]


def _ohlcv(
    closes: FloatArray,
    opens: FloatArray,
    highs: FloatArray,
    lows: FloatArray,
    volumes: FloatArray,
) -> pd.DataFrame:
    """Assemble a research price frame, enforcing high >= max(open, close) >= min(...) >= low.

    Notes:
        The clamp is a no-op on well-formed inputs; it exists so a resampled real bar can never
        produce a frame the canonical PriceBar contract would reject.
    """
    body_high = np.maximum(opens, closes)
    body_low = np.minimum(opens, closes)
    return pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(highs, body_high),
            "low": np.minimum(lows, body_low),
            "close": closes,
            "volume": volumes,
        },
        index=pd.date_range(_START, periods=len(closes), freq="B", tz="UTC"),
    )[_COLUMNS]


def iid_normal_null(
    n_bars: int,
    *,
    seed: int,
    drift: float = 0.0003,
    vol: float = 0.012,
    start_price: float = 100.0,
) -> pd.DataFrame:
    """A price frame whose returns are iid normal — the textbook null (ADR-036).

    Notes:
        Every bar's open/high/low is drawn independently too, so there is no serial dependence for
        any catalog strategy to trade: not in returns, not in the overnight gap, not in the
        intrabar range. Clean but well-behaved — pair it with `bootstrap_null` for fat tails.
    """
    if n_bars < 1:
        raise ValueError("n_bars must be >= 1")
    rng = np.random.default_rng(seed)
    closes = start_price * np.cumprod(1.0 + rng.normal(drift, vol, n_bars))
    opens = closes * (1.0 + rng.normal(0.0, vol / 3.0, n_bars))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0.0, vol / 2.0, n_bars)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0.0, vol / 2.0, n_bars)))
    volumes = rng.integers(1_000_000, 5_000_000, n_bars).astype(float)
    return _ohlcv(closes, opens, highs, lows, volumes)


def bootstrap_null(
    source: pd.DataFrame, n_bars: int, *, seed: int, start_price: float | None = None
) -> pd.DataFrame:
    """A price frame built by resampling `source`'s own bars iid WITH REPLACEMENT (ADR-036).

    Each draw carries a real bar's return together with that bar's open/high/low/volume geometry,
    so the marginal distribution — fat tails, skew, realized drift and volatility, gap size — is
    preserved exactly while every serial dependence is destroyed exactly. Every catalog strategy
    trades on serial structure, so its true edge here is zero by construction: unlike a synthetic
    process, this null cannot be dismissed as unrealistically well-behaved.
    """
    if n_bars < 1:
        raise ValueError("n_bars must be >= 1")
    returns = source["close"].pct_change().dropna()
    if returns.empty:
        raise ValueError("source frame has no returns to resample (need >= 2 bars)")

    bars = source.loc[returns.index]
    rng = np.random.default_rng(seed)
    draw = rng.integers(0, len(returns), n_bars)
    base = float(source["close"].iloc[0]) if start_price is None else start_price
    closes = base * np.cumprod(1.0 + returns.to_numpy()[draw])
    return _ohlcv(
        closes,
        closes * (bars["open"] / bars["close"]).to_numpy()[draw],
        closes * (bars["high"] / bars["close"]).to_numpy()[draw],
        closes * (bars["low"] / bars["close"]).to_numpy()[draw],
        bars["volume"].to_numpy()[draw],
    )


def calibrate_gate(
    frames: Mapping[str, pd.DataFrame],
    strategy_names: Sequence[str],
    *,
    config: GateConfig | None = None,
    n_per_param: int = 3,
) -> NullCalibration:
    """Run the unmodified search + gate over null price frames and report how often it graduates.

    Notes:
        Deliberately takes no ExperimentStore: a null run is not a hypothesis about a real symbol
        and must never reach the research pool, the MinTRL denominator, or the leaderboard.
        A symbol that cannot be searched at all (too short to split) is recorded in `errors` and
        excluded from the denominator — counting it as a non-graduate would understate the rate.
    """
    if not frames:
        raise ValueError("need at least one null symbol to calibrate")
    gate_config = config or GateConfig()

    experiments: list[Experiment] = []
    holdout_years: list[float] = []
    errors: dict[str, str] = {}
    for symbol, frame in frames.items():
        try:
            experiment = run_search(
                frame,
                symbol,
                list(strategy_names),
                config=gate_config,
                n_per_param=n_per_param,
                rationale="ADR-036 null calibration",
            )
            _, sealed = split_holdout(frame, symbol)
        except ValueError as exc:
            errors[symbol] = str(exc)
            continue
        experiments.append(experiment)
        holdout_years.append(sealed.n_bars / _TRADING_DAYS)

    if not experiments:
        raise ValueError("need at least one null symbol that can be searched")

    n_symbols = len(experiments)
    graduates = [e for e in experiments if e.graduate is not None]
    cleared = [
        e
        for e in graduates
        if e.graduate is not None
        and e.graduate.holdout_sharpe
        > expected_max_sharpe_under_null(n_symbols, e.graduate.holdout_n_bars / _TRADING_DAYS)
    ]
    return NullCalibration(
        n_symbols=n_symbols,
        n_graduates=len(graduates),
        false_graduation_rate=len(graduates) / n_symbols,
        n_clear_deflation_bar=len(cleared),
        # Reported at the median holdout length so the headline bar is well defined even when
        # nothing graduated; survival above is always judged per graduate, as the leaderboard does.
        deflation_bar=expected_max_sharpe_under_null(n_symbols, median(holdout_years)),
        max_deflated_sharpe=max(t.deflated_sharpe for e in experiments for t in e.trials),
        max_holdout_sharpe=max(
            (e.graduate.holdout_sharpe for e in graduates if e.graduate), default=None
        ),
        graduate_symbols=[e.symbol for e in graduates],
        errors=errors,
        gate_config_version=gate_config.version_hash,
    )
