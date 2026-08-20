from collections.abc import Mapping, Sequence
from datetime import datetime
from statistics import median
from typing import Any, NamedTuple

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from app.research.backtesting.engine import DEFAULT_COST_RATE
from app.research.backtesting.manifest import compute_parameter_hash
from app.research.lab.candidate_budget import allocate_catalog_candidate_budget
from app.research.lab.experiment import Experiment, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.holdout import split_holdout
from app.research.lab.search import run_search
from app.research.lab.universe import expected_max_sharpe_under_null

_TRADING_DAYS = 252
_COLUMNS = ["open", "high", "low", "close", "volume"]
_START = "2010-01-04"


class NullGraduate(BaseModel):
    """A false graduate, kept with everything the ADR-018 bar must be recomputed against.

    Notes:
        The bar is a function of how many symbols were searched in TOTAL, so a shard cannot decide
        survival on its own — `merge_calibrations` re-judges every graduate at the combined N
        (ADR-037).
    """

    model_config = ConfigDict(frozen=True)

    symbol: str
    holdout_sharpe: float
    holdout_n_bars: int
    deflated_sharpe: float


class NullCalibration(BaseModel):
    """The gate's measured behavior on a universe with no edge by construction (ADR-036).

    `false_graduation_rate` is a Type-I error for the WHOLE pipeline — search, DSR, PBO, MinTRL,
    holdout and beat-buy-and-hold together — which none of those components' individual guarantees
    implies. ADR-044 versions both the gate thresholds and the resolved search family; re-measure
    whenever either changes.
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    n_graduates: int
    false_graduation_rate: float
    n_clear_deflation_bar: int
    deflation_bar: float
    max_deflated_sharpe: float
    max_holdout_sharpe: float | None
    graduates: list[NullGraduate]
    # One entry per SEARCHED symbol (not per graduate): the merged bar is reported at the median
    # holdout length, which is only exact if the lengths themselves survive sharding (ADR-037).
    holdout_years: list[float]
    # ADR-051: the total history each null symbol was judged on, one entry per SEARCHED symbol. A
    # null and a real hunt are only comparable at the same length, and an empty list means an
    # artifact predating this field — never that the run saw no bars.
    n_bars: list[int] = []
    # ADR-038: the finalist trial's walk-forward mean OOS Sharpe, one per searched symbol. Under a
    # null this is the distribution a walk-forward floor would have to clear, which is the evidence
    # ADR-038 requires before promoting the statistic from a diagnostic to a gate criterion.
    walk_forward_oos_sharpes: list[float] = []
    # ADR-039: the same, for the purged folds. Separate list because the two statistics have
    # different null distributions and a floor argued from one says nothing about the other.
    purged_cv_oos_sharpes: list[float] = []
    errors: dict[str, str]
    gate_config_version: str
    # ADR-044: the result measures search + gate, not thresholds alone. Old committed artifacts
    # remain readable but honestly advertise that their resolved hypothesis family was not hashed.
    search_config_version: str = "legacy-unspecified"
    # ADR-047: calibration must say whether it measured production's adaptive second pass.
    # Legacy artifacts were coarse-only, so False is the truthful compatibility default.
    refine: bool = False
    refine_span: float = 0.25
    null_mode: str = "unspecified"

    @property
    def graduate_symbols(self) -> list[str]:
        return [g.symbol for g in self.graduates]

    @property
    def purged_cv_null_percentiles(self) -> tuple[float, float, float] | None:
        """(median, p95, max) purged-CV OOS Sharpe under the null — ADR-039's candidate floor."""
        return _percentiles(self.purged_cv_oos_sharpes)

    @property
    def walk_forward_null_percentiles(self) -> tuple[float, float, float] | None:
        """(median, p95, max) walk-forward OOS Sharpe under the null — ADR-038's candidate floor.

        Notes:
            None when nothing was measured, so "no walk-forward data" can never be mistaken for
            "the null walks forward at 0.0".
        """
        return _percentiles(self.walk_forward_oos_sharpes)


# Widened past the repo's usual NDArray[float64]: numpy types these products as
# floating[Any], and _ohlcv only feeds them to a DataFrame constructor.
FloatArray = npt.NDArray[np.floating[Any]]

# Changes whenever the procedure that counts/prices searched hypotheses changes. The resolved grid
# alone is insufficient identity when the same configs receive a different multiple-testing price.
_TRIAL_ACCOUNTING_VERSION = "whole-search-budgeted-robust-iqr-v3"
_CANDIDATE_BUDGET_VERSION = "fair-family-maximin-v1"


def calibration_search_version(
    strategy_names: Sequence[str],
    *,
    n_per_param: int,
    config: GateConfig,
    refine: bool = True,
    refine_span: float = 0.25,
) -> str:
    """Fingerprint the exact catalog-derived hypothesis family calibrated by a run (ADR-044).

    Families are canonicalized because ADR-048 makes caller order irrelevant. The concrete budgeted
    grids are hashed rather than catalog bounds: they are the configurations `run_search` actually
    tests after invalid combinations and fair allocation have been applied.
    """
    allocation = allocate_catalog_candidate_budget(
        strategy_names,
        n_per_param=n_per_param,
        budget=config.trial_budget,
        refine=refine,
    )
    strategies = [
        {
            "name": name,
            "configs": [strategy.parameters for strategy in grid],
        }
        for name, grid in allocation.families.items()
    ]
    return compute_parameter_hash(
        {
            "gate_config_version": config.version_hash,
            "trial_accounting_version": _TRIAL_ACCOUNTING_VERSION,
            "candidate_budget_version": _CANDIDATE_BUDGET_VERSION,
            "n_per_param": n_per_param,
            "refine": refine,
            "refine_span": refine_span if refine else None,
            "refinement_reserve": allocation.refinement_reserve,
            "strategies": strategies,
        }
    )


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


def drop_incomplete_bars(frame: pd.DataFrame, *, asof: datetime) -> pd.DataFrame:
    """Drop bars dated on or after `asof`'s day — the session still forming (ADR-036).

    Notes:
        A calibration is a property of a GateConfig version, so two runs on the same day must
        agree. Without this the bootstrap null resamples a pool that includes today's in-progress
        bar and drifts intraday, while the iid null stays bit-identical. Across DAYS the source
        frame still grows, which is correct: a calibration is dated.
    """
    cutoff = pd.Timestamp(asof).tz_convert("UTC").normalize()
    trimmed = frame[frame.index < cutoff]
    if trimmed.empty:
        raise ValueError(f"no completed bars before {cutoff.date()}")
    return trimmed


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


class PowerCalibration(BaseModel):
    """The gate's measured ability to DETECT a planted edge (ADR-041) — the Type-II half.

    Notes:
        `detection_rate` is power of the gate as such; `n_clear_deflation_bar` is power against the
        standard the project actually holds itself to (ADR-018), and it is the number that
        interprets "0 of 40 graduates clear the bar". An AR(1) edge is stationary and always-on,
        so this is an UPPER BOUND on power against real, intermittent edges: a low number here is
        damning, a high one is not a clean bill of health.
    """

    model_config = ConfigDict(frozen=True)

    n_symbols: int
    n_detected: int
    detection_rate: float
    n_clear_deflation_bar: int
    deflation_bar: float
    # Which process was planted, so an artifact is reproducible without its workflow file. `phi`
    # describes ADR-041's AR(1); `half_life`/`deviation_share` describe ADR-042's band reversion.
    edge: str = "ar1"
    phi: float | None = None
    half_life: float | None = None
    deviation_share: float | None = None
    oracle_sharpes: list[float]
    # ADR-055: the same oracle charged the cost model the catalog pays. The gross list above is
    # what ADR-041/042 published and is kept unchanged; this one is what a capture ratio should be
    # divided by, since its numerator paid those costs. Empty means an artifact predating ADR-055.
    net_oracle_sharpes: list[float] = []
    # ADR-045: one max-DSR finalist per SEARCHED symbol, including non-detections. Conditioning
    # this list on graduation would select lucky captures and inflate the reported ratio.
    # Defaulted so power artifacts written before ADR-045 remain readable and report no capture.
    finalist_observed_sharpes: list[float] = []
    # ADR-049: independent component pass counts make a composite zero-power result diagnosable.
    # Empty means a legacy artifact did not preserve attribution; it never means zero passes.
    gate_pass_counts: dict[str, int] = Field(default_factory=dict)
    holdout_years: list[float]
    # ADR-051: the history each planted-edge symbol was searched over, one entry per SEARCHED
    # symbol. Power measured short is a lower bound on the power available, so an artifact that
    # does not state its length cannot bound anything. Empty means a run predating the field.
    n_bars: list[int] = []
    errors: dict[str, str]
    gate_config_version: str
    search_config_version: str = "legacy-unspecified"
    refine: bool = False
    refine_span: float = 0.25

    @property
    def oracle_sharpe_percentiles(self) -> tuple[float, float, float] | None:
        """(median, p95, max) of the planted effect size actually realized in these frames."""
        return _percentiles(self.oracle_sharpes)

    @property
    def net_oracle_sharpe_percentiles(self) -> tuple[float, float, float] | None:
        """(median, p95, max) of the planted effect size NET of transaction costs (ADR-055)."""
        return _percentiles(self.net_oracle_sharpes)

    @property
    def net_capture_ratio(self) -> float | None:
        """`capture_ratio` against the effect size the catalog could actually have kept (ADR-055).

        Both numerator and denominator are now net of the same cost model. Higher than the gross
        ratio by construction — that is the denominator being corrected, not the catalog improving.
        """
        if (
            len(self.finalist_observed_sharpes) != self.n_symbols
            or len(self.net_oracle_sharpes) != self.n_symbols
        ):
            return None
        oracle = median(self.net_oracle_sharpes)
        if oracle <= 0.0:
            return None
        return median(self.finalist_observed_sharpes) / oracle

    @property
    def capture_ratio(self) -> float | None:
        """Selection-biased upper bound on how much of the planted edge the catalog captures.

        Both lists must cover every searched symbol. Partial or legacy artifacts return None rather
        than silently changing the denominator. A non-positive median oracle has no available edge
        to express as a meaningful capture fraction.
        """
        if (
            len(self.finalist_observed_sharpes) != self.n_symbols
            or len(self.oracle_sharpes) != self.n_symbols
        ):
            return None
        oracle = median(self.oracle_sharpes)
        if oracle <= 0.0:
            return None
        return median(self.finalist_observed_sharpes) / oracle


def autocorrelated_edge(
    n_bars: int,
    *,
    seed: int,
    phi: float,
    vol: float = 0.012,
    drift: float = 0.0003,
    start_price: float = 100.0,
) -> pd.DataFrame:
    """A price frame whose returns follow AR(1) — a planted, tradeable edge (ADR-041).

    Notes:
        `phi < 0` is mean reversion (the RSI/Bollinger family's claim), `phi > 0` is trend
        persistence (the SMA/MACD/Donchian family's). Bar geometry is built exactly as
        `iid_normal_null` builds it, so the ONLY difference from the null is the serial dependence
        — which is the thing every catalog strategy claims to trade. `phi` must be in (-1, 1) or
        the process is not stationary.
    """
    if n_bars < 1:
        raise ValueError("n_bars must be >= 1")
    if not -1.0 < phi < 1.0:
        raise ValueError("phi must be in (-1, 1) for a stationary process")

    rng = np.random.default_rng(seed)
    shocks = rng.normal(0.0, vol, n_bars)
    returns = np.empty(n_bars, dtype=float)
    previous = 0.0
    for i, shock in enumerate(shocks):
        previous = phi * previous + shock
        returns[i] = drift + previous

    closes = start_price * np.cumprod(1.0 + returns)
    opens = closes * (1.0 + rng.normal(0.0, vol / 3.0, n_bars))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0.0, vol / 2.0, n_bars)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0.0, vol / 2.0, n_bars)))
    volumes = rng.integers(1_000_000, 5_000_000, n_bars).astype(float)
    return _ohlcv(closes, opens, highs, lows, volumes)


def oracle_sharpe(frame: pd.DataFrame, *, phi: float, cost_rate: float = 0.0) -> float:
    """Annualized Sharpe of `position_t = sign(phi * r_{t-1})` on `frame` (ADR-041).

    Notes:
        The sign of the AR(1) conditional mean, so it is the best any causal sign-taking strategy
        could do on this series — scored with the same one-bar lag the backtest engine applies.
        Measured on the data the search sees rather than derived, so the reported effect size
        carries no theory that could be silently wrong.
    """
    returns = frame["close"].pct_change().dropna()
    return oracle_sharpe_of(frame, phi * returns.shift(1), cost_rate=cost_rate)


def oracle_sharpe_of(
    frame: pd.DataFrame, conditional_mean: "pd.Series[float]", *, cost_rate: float = 0.0
) -> float:
    """Annualized Sharpe of `position_t = sign(E[r_t | F_{t-1}])` on `frame` (ADR-042).

    Notes:
        The generic form of `oracle_sharpe`: any planted process can report its effect size on the
        same scale as ADR-041's AR(1) one by handing over its own conditional mean. `conditional_mean`
        must already be lagged — indexed by the bar it PREDICTS, using only information available
        before that bar.

        `cost_rate` charges turnover the way `BacktestEngine` charges the catalog (ADR-055). It
        defaults to ZERO, which is the gross definition every committed power artifact was measured
        under; changing that default would silently restate published effect sizes. A sign oracle
        turns over heavily, so the net figure is materially lower and, being a *sign* strategy
        rather than a sized one, is a LOWER bound on what perfect knowledge could achieve net.
    """
    if cost_rate < 0:
        raise ValueError("cost_rate must be >= 0")
    returns = frame["close"].pct_change().dropna()
    if len(returns) < 3:
        return 0.0
    position = np.sign(conditional_mean.reindex(returns.index)).fillna(0.0)
    turnover = position.diff().abs().fillna(position.abs())
    realized = (position * returns - turnover * cost_rate).dropna()
    std = float(realized.std())
    if std == 0.0:
        return 0.0
    return float(np.sqrt(_TRADING_DAYS) * realized.mean() / std)


class PlantedEdge(NamedTuple):
    """A planted-edge frame with the latent state that makes its effect size measurable.

    Notes:
        `conditional_mean` is `E[r_t | F_{t-1}]`, indexed by the bar it predicts — what an oracle
        with knowledge of the process, but not of the future, would act on. `deviation` is the
        latent distance from the level, kept because `half_life` is a statement about IT and not
        about the returns.
    """

    frame: pd.DataFrame
    conditional_mean: "pd.Series[float]"
    deviation: "pd.Series[float]"


def mean_reverting_edge(
    n_bars: int,
    *,
    seed: int,
    half_life: float,
    deviation_share: float,
    total_vol: float = 0.012,
    drift: float = 0.0003,
    start_price: float = 100.0,
) -> PlantedEdge:
    """A price that wanders (random-walk level) and reverts to where it wandered (ADR-042).

    Notes:
        `half_life` is the number of bars in which a deviation from the level decays by half, i.e.
        the horizon a band/oscillator strategy is meant to trade — the parameter ADR-041's lag-1
        AR(1) process could not express. `deviation_share` is the share of total return variance
        the reverting component contributes; the level volatility is solved for so realized
        volatility stays at `total_vol` at every horizon, without which a horizon sweep would move
        the volatility and the effect size at the same time and confound all three.

        Effect size is bounded by the horizon: only `(1 - rho) / 2` of the deviation's variance is
        predictable one bar ahead, so a slow band cannot be as tradeable as a fast one — see
        ADR-042 for why the sweep is therefore read in two tiers.
    """
    if n_bars < 1:
        raise ValueError("n_bars must be >= 1")
    if half_life <= 0.0:
        raise ValueError("half_life must be > 0 bars")
    if not 0.0 < deviation_share <= 1.0:
        raise ValueError("deviation_share must be in (0, 1]")

    rho = 0.5 ** (1.0 / half_life)
    deviation_vol = total_vol * np.sqrt(deviation_share / (2.0 * (1.0 - rho)))
    level_vol = total_vol * np.sqrt(1.0 - deviation_share)

    rng = np.random.default_rng(seed)
    shocks = rng.normal(0.0, deviation_vol * np.sqrt(1.0 - rho**2), n_bars)
    deviations = np.empty(n_bars, dtype=float)
    previous = 0.0
    for i, shock in enumerate(shocks):
        previous = rho * previous + shock
        deviations[i] = previous

    levels = np.cumsum(rng.normal(drift, level_vol, n_bars))
    closes = start_price * np.exp(levels + deviations)
    opens = closes * (1.0 + rng.normal(0.0, total_vol / 3.0, n_bars))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0.0, total_vol / 2.0, n_bars)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0.0, total_vol / 2.0, n_bars)))
    volumes = rng.integers(1_000_000, 5_000_000, n_bars).astype(float)
    frame = _ohlcv(closes, opens, highs, lows, volumes)

    deviation = pd.Series(deviations, index=frame.index)
    # E[r_t | F_{t-1}] = drift + (rho - 1) * dev_{t-1}: the level is a martingale, so everything
    # predictable about the next bar is the part of the deviation that is about to decay away.
    conditional_mean = drift + (rho - 1.0) * deviation.shift(1)
    return PlantedEdge(frame=frame, conditional_mean=conditional_mean, deviation=deviation)


def measure_power(
    frames: Mapping[str, pd.DataFrame],
    strategy_names: Sequence[str],
    *,
    phi: float | None = None,
    oracle_sharpes: Mapping[str, float] | None = None,
    net_oracle_sharpes: Mapping[str, float] | None = None,
    edge: str = "ar1",
    half_life: float | None = None,
    deviation_share: float | None = None,
    config: GateConfig | None = None,
    n_per_param: int = 3,
    refine: bool = True,
    refine_span: float = 0.25,
) -> PowerCalibration:
    """Run the unmodified search + gate over frames with a PLANTED edge and count detections.

    Notes:
        Give `phi` for ADR-041's AR(1) process and the effect size is measured here; give
        `oracle_sharpes` for any other planted process (ADR-042) and the caller supplies the effect
        size it measured with `oracle_sharpe_of`. Exactly one, because defaulting either way would
        mislabel the effect size of a whole published run.

        Deliberately takes no ExperimentStore, exactly as `calibrate_gate` does not: a synthetic
        symbol is not a hypothesis about a real one and must never reach the research pool or the
        MinTRL denominator (ADR-036/041).
    """
    if not frames:
        raise ValueError("need at least one symbol to measure power")
    one_source = "pass exactly one of phi (AR(1)) or oracle_sharpes (any other process)"
    if oracle_sharpes is None:
        if phi is None:
            raise ValueError(one_source)
        if net_oracle_sharpes is not None:
            raise ValueError("net_oracle_sharpes belongs with oracle_sharpes, not with phi")
        oracle_sharpes = {symbol: oracle_sharpe(frame, phi=phi) for symbol, frame in frames.items()}
        net_oracle_sharpes = {
            symbol: oracle_sharpe(frame, phi=phi, cost_rate=DEFAULT_COST_RATE)
            for symbol, frame in frames.items()
        }
    elif phi is not None:
        raise ValueError(one_source)
    else:
        missing = sorted(set(frames) - set(oracle_sharpes))
        if missing:
            raise ValueError(f"no measured oracle Sharpe for {', '.join(missing)}")
        if net_oracle_sharpes is not None:
            missing = sorted(set(frames) - set(net_oracle_sharpes))
            if missing:
                raise ValueError(f"no measured net oracle Sharpe for {', '.join(missing)}")
    gate_config = config or GateConfig()

    experiments: list[Experiment] = []
    holdout_years: list[float] = []
    n_bars: list[int] = []
    oracles: list[float] = []
    net_oracles: list[float] = []
    finalist_observed_sharpes: list[float] = []
    errors: dict[str, str] = {}
    for symbol, frame in frames.items():
        try:
            experiment = run_search(
                frame,
                symbol,
                list(strategy_names),
                config=gate_config,
                n_per_param=n_per_param,
                refine=refine,
                refine_span=refine_span,
                rationale="ADR-041 power calibration",
            )
            _, sealed = split_holdout(frame, symbol)
        except ValueError as exc:
            errors[symbol] = str(exc)
            continue
        experiments.append(experiment)
        holdout_years.append(sealed.n_bars / _TRADING_DAYS)
        n_bars.append(len(frame))
        oracles.append(oracle_sharpes[symbol])
        if net_oracle_sharpes is not None:
            net_oracles.append(net_oracle_sharpes[symbol])
        finalist_observed_sharpes.append(_finalist(experiment).observed_sharpe)

    if not experiments:
        raise ValueError("need at least one symbol that can be searched")

    n_symbols = len(experiments)
    detected = [e for e in experiments if e.graduate is not None]
    gate_results = [e.best_gate_result for e in experiments if e.best_gate_result is not None]
    return PowerCalibration(
        n_symbols=n_symbols,
        n_detected=len(detected),
        detection_rate=len(detected) / n_symbols,
        n_clear_deflation_bar=sum(
            e.graduate.holdout_sharpe
            > expected_max_sharpe_under_null(n_symbols, e.graduate.holdout_n_bars / _TRADING_DAYS)
            for e in detected
            if e.graduate is not None
        ),
        deflation_bar=expected_max_sharpe_under_null(n_symbols, median(holdout_years)),
        edge=edge,
        phi=phi,
        half_life=half_life,
        deviation_share=deviation_share,
        oracle_sharpes=oracles,
        net_oracle_sharpes=net_oracles,
        finalist_observed_sharpes=finalist_observed_sharpes,
        n_bars=n_bars,
        gate_pass_counts={
            "dsr": sum(result.dsr_ok for result in gate_results),
            "pbo": sum(result.pbo_ok for result in gate_results),
            "stability": sum(result.stability_ok for result in gate_results),
            "mintrl": sum(result.mintrl_ok for result in gate_results),
            "holdout": sum(result.holdout_ok for result in gate_results),
            "beats_buy_and_hold": sum(result.beats_buy_and_hold_ok for result in gate_results),
        },
        holdout_years=holdout_years,
        errors=errors,
        gate_config_version=gate_config.version_hash,
        search_config_version=calibration_search_version(
            strategy_names,
            n_per_param=n_per_param,
            config=gate_config,
            refine=refine,
            refine_span=refine_span,
        ),
        refine=refine,
        refine_span=refine_span,
    )


def _percentiles(values: Sequence[float]) -> tuple[float, float, float] | None:
    """(median, p95, max), or None when nothing was measured — so "no data" can never be mistaken
    for "the null scores 0.0"."""
    if not values:
        return None
    array = np.asarray(values, dtype=float)
    return float(np.median(array)), float(np.percentile(array, 95)), float(array.max())


def _finalist(experiment: Experiment) -> Trial:
    """The max-DSR trial — the same one run_search sends to the gate."""
    return max(experiment.trials, key=lambda t: t.deflated_sharpe)


def calibrate_gate(
    frames: Mapping[str, pd.DataFrame],
    strategy_names: Sequence[str],
    *,
    config: GateConfig | None = None,
    n_per_param: int = 3,
    refine: bool = True,
    refine_span: float = 0.25,
    null_mode: str = "unspecified",
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
    n_bars: list[int] = []
    errors: dict[str, str] = {}
    for symbol, frame in frames.items():
        try:
            experiment = run_search(
                frame,
                symbol,
                list(strategy_names),
                config=gate_config,
                n_per_param=n_per_param,
                refine=refine,
                refine_span=refine_span,
                rationale="ADR-036 null calibration",
            )
            _, sealed = split_holdout(frame, symbol)
        except ValueError as exc:
            errors[symbol] = str(exc)
            continue
        experiments.append(experiment)
        holdout_years.append(sealed.n_bars / _TRADING_DAYS)
        n_bars.append(len(frame))

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
        graduates=[
            NullGraduate(
                symbol=e.symbol,
                holdout_sharpe=e.graduate.holdout_sharpe,
                holdout_n_bars=e.graduate.holdout_n_bars,
                # The finalist is the max-DSR trial by construction in run_search, and Graduate
                # does not carry the statistic itself.
                deflated_sharpe=max(t.deflated_sharpe for t in e.trials),
            )
            for e in graduates
            if e.graduate is not None
        ],
        holdout_years=holdout_years,
        n_bars=n_bars,
        walk_forward_oos_sharpes=[
            wf for e in experiments if (wf := _finalist(e).walk_forward_oos_sharpe) is not None
        ],
        purged_cv_oos_sharpes=[
            cv for e in experiments if (cv := _finalist(e).purged_cv_oos_sharpe) is not None
        ],
        errors=errors,
        gate_config_version=gate_config.version_hash,
        search_config_version=calibration_search_version(
            strategy_names,
            n_per_param=n_per_param,
            config=gate_config,
            refine=refine,
            refine_span=refine_span,
        ),
        refine=refine,
        refine_span=refine_span,
        null_mode=null_mode,
    )


class PowerSweep(BaseModel):
    """One power curve: the cells of a single planted process, at one procedure and one history.

    Notes:
        A list, not a merge. Null shards are draws from one experiment and pool into a single rate;
        power cells plant different effect sizes and are each judged at their own N, so pooling
        them would report a detection rate for no stated effect size (ADR-053).
    """

    model_config = ConfigDict(frozen=True)

    edge: str
    gate_config_version: str
    search_config_version: str
    n_bars: int
    cells: list[PowerCalibration]


def collect_power_sweep(cells: Sequence[PowerCalibration]) -> PowerSweep:
    """Order one process's power cells into a committed record, refusing incoherent sweeps.

    Notes:
        The three refusals are the whole value of the function. Cells of different processes,
        different resolved procedures, or different history lengths are not points on one curve,
        and a file that silently held them would be read as if they were.
    """
    if not cells:
        raise ValueError("need at least one power cell to collect a sweep")
    edges = {c.edge for c in cells}
    if len(edges) > 1:
        raise ValueError(f"cannot collect cells with different edge: {sorted(edges)}")
    versions = {c.gate_config_version for c in cells}
    if len(versions) > 1:
        raise ValueError(
            f"cannot collect cells with different gate_config_version: {sorted(versions)}"
        )
    search_versions = {c.search_config_version for c in cells}
    if len(search_versions) > 1:
        raise ValueError(
            f"cannot collect cells with different search_config_version: {sorted(search_versions)}"
        )
    lengths = {int(median(c.n_bars)) for c in cells if c.n_bars}
    if len(lengths) > 1:
        raise ValueError(f"cannot collect cells with different n_bars: {sorted(lengths)}")

    def _key(cell: PowerCalibration) -> float:
        # An AR(1) sweep is indexed by phi and a band sweep by half-life; the other is None on each.
        return cell.phi if cell.phi is not None else (cell.half_life or 0.0)

    return PowerSweep(
        edge=edges.pop(),
        gate_config_version=versions.pop(),
        search_config_version=search_versions.pop(),
        n_bars=lengths.pop() if lengths else 0,
        cells=sorted(cells, key=_key),
    )


def merge_calibrations(shards: Sequence[NullCalibration]) -> NullCalibration:
    """Combine sharded null runs into one calibration judged at the COMBINED N (ADR-037).

    Notes:
        Not an average of the shards' rates. The ADR-018 deflation bar grows with the number of
        symbols searched, so survival is re-decided here for every false graduate; and the shards'
        denominators differ whenever a symbol was unsearchable, so the rate is recomputed from the
        merged counts. Merging is refused across gate configs or null modes — a false-graduation
        rate describes one gate applied to one kind of null, and silently pooling two of them would
        produce a number that describes neither.
    """
    if not shards:
        raise ValueError("need at least one shard to merge")
    versions = {s.gate_config_version for s in shards}
    if len(versions) > 1:
        raise ValueError(
            f"cannot merge shards with different gate_config_version: {sorted(versions)}"
        )
    search_versions = {s.search_config_version for s in shards}
    if len(search_versions) > 1:
        raise ValueError(
            f"cannot merge shards with different search_config_version: {sorted(search_versions)}"
        )
    modes = {s.null_mode for s in shards}
    if len(modes) > 1:
        raise ValueError(f"cannot merge shards with different null_mode: {sorted(modes)}")

    n_symbols = sum(s.n_symbols for s in shards)
    graduates = [g for s in shards for g in s.graduates]
    holdout_years = [y for s in shards for y in s.holdout_years]
    n_bars = [n for s in shards for n in s.n_bars]
    return NullCalibration(
        n_symbols=n_symbols,
        n_graduates=len(graduates),
        false_graduation_rate=len(graduates) / n_symbols,
        n_clear_deflation_bar=sum(
            g.holdout_sharpe
            > expected_max_sharpe_under_null(n_symbols, g.holdout_n_bars / _TRADING_DAYS)
            for g in graduates
        ),
        deflation_bar=expected_max_sharpe_under_null(n_symbols, median(holdout_years)),
        max_deflated_sharpe=max(s.max_deflated_sharpe for s in shards),
        max_holdout_sharpe=max((g.holdout_sharpe for g in graduates), default=None),
        graduates=graduates,
        holdout_years=holdout_years,
        n_bars=n_bars,
        walk_forward_oos_sharpes=[v for s in shards for v in s.walk_forward_oos_sharpes],
        purged_cv_oos_sharpes=[v for s in shards for v in s.purged_cv_oos_sharpes],
        errors={sym: why for s in shards for sym, why in s.errors.items()},
        gate_config_version=versions.pop(),
        search_config_version=search_versions.pop(),
        refine=shards[0].refine,
        refine_span=shards[0].refine_span,
        null_mode=modes.pop(),
    )
