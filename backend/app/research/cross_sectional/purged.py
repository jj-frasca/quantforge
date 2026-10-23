"""Restricted direct-price-operand purged diagnostics (ADR-325; López de Prado 2018 ch7).

Source separation is not independence or causal selection. ADR-348/350 add only
runtime-attributed Cython high/Alpha9 support; other rolling/static recipes
retain FINDING-272 limitations.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from numbers import Integral
from typing import Final, Literal

import numpy as np
import numpy.typing as npt
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.research.cross_sectional.registry import (
    CrossSectionalStrategy,
    Params,
    alpha9_factory,
    high_proximity_factory,
    momentum_factory,
    reversal_factory,
    short_term_reversal_factory,
)
from app.research.trial_counts import require_trial_count
from app.validation.purged_cv import PurgedCVResult, purged_cv_evaluate, purged_kfold_splits

Reason = Literal[
    "unsupported_factory",
    "unsupported_parameters",
    "unsupported_price_dtype",
    "unsupported_pandas_version",
    "unsupported_rolling_engine",
]
Rule = Literal["shifted-momentum-v1", "shifted-reversal-v1", "rolling-high-v1", "rolling-alpha9-v1"]
HIGH_PURGED_METHOD: Final = (
    "restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2"
)
ALPHA9_PURGED_METHOD: Final = (
    "restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3"
)


@dataclass(frozen=True)
class HighRuntime:
    """Observed high/Alpha9 matrix domain; historical name, not provenance proof."""

    version: str
    use_numba: bool | None


def capture_high_runtime() -> HighRuntime:
    """Observe standard dispatch; unknown versions make no engine-option claim."""
    version = pd.__version__
    return HighRuntime(version, pd.get_option("compute.use_numba") if version == "3.0.6" else None)


def requested_fold_count(value: object) -> int:
    count = require_trial_count(value, minimum=1, parameter="purged_folds")
    if count < 2:
        raise ValueError("purged_folds must be >= 2")
    return count


def kept_geometry(n_bars: int, requested_folds: int, embargo: int) -> tuple[int, int, int]:
    """Prefix end, suffix start and union cardinality, without arrays (ADR-325)."""
    n_bars = require_trial_count(n_bars, minimum=1, parameter="purged bars")
    requested_folds = requested_fold_count(requested_folds)
    embargo = require_trial_count(embargo, minimum=0, parameter="purged embargo")
    if n_bars < requested_folds:
        raise ValueError("purged bars must cover requested folds")
    q, r = divmod(n_bars, requested_folds)
    lo, hi = 0, requested_folds
    while lo < hi:
        j = (lo + hi) // 2
        start = q * j + min(j, r)
        end = start + q + int(j < r)
        if end + embargo >= n_bars:
            hi = j
        else:
            lo = j + 1
    prefix_end = lo
    lo, hi = 0, requested_folds
    while lo < hi:
        j = (lo + hi) // 2
        if q * j + min(j, r) > embargo:
            hi = j
        else:
            lo = j + 1
    suffix_start = lo
    return prefix_end, suffix_start, prefix_end + requested_folds - max(prefix_end, suffix_start)


class PurgedDiagnostic(BaseModel):
    """Immutable compact evidence, not an allocated-config or source-provenance replay."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    method: Literal[
        "restricted-shift-family-purged-equal-weight-continuation-v1",
        "restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2",
        "restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3",
    ] = "restricted-shift-family-purged-equal-weight-continuation-v1"
    status: Literal["measured", "unsupported", "no_usable_folds"]
    n_bars: int
    requested_folds: int
    floor: int
    reason: Reason | None = None
    dependency_rule: Rule | None = None
    max_price_lag: int | None = None
    embargo: int | None = None
    kept_fold_ordinals: tuple[int, ...] | None = None
    mean_oos_sharpe: float | None = Field(default=None, allow_inf_nan=False)
    mean_oos_hold_sharpe: float | None = Field(default=None, allow_inf_nan=False)

    @field_validator("n_bars", "max_price_lag", mode="before")
    @classmethod
    def _positive_count(cls, value: object) -> int | None:
        return (
            None
            if value is None
            else require_trial_count(value, minimum=1, parameter="purged count")
        )

    @field_validator("floor", "embargo", mode="before")
    @classmethod
    def _nonnegative_count(cls, value: object) -> int | None:
        return (
            None
            if value is None
            else require_trial_count(value, minimum=0, parameter="purged embargo")
        )

    @field_validator("requested_folds", mode="before")
    @classmethod
    def _requested_count(cls, value: object) -> int:
        return requested_fold_count(value)

    @field_validator("kept_fold_ordinals", mode="before")
    @classmethod
    def _ordinals(cls, value: object) -> tuple[int, ...] | None:
        if value is None:
            return None
        if not isinstance(value, (tuple, list)):
            raise ValueError("kept fold identities must be a sequence")
        return tuple(
            require_trial_count(j, minimum=0, parameter="kept fold ordinal") for j in value
        )

    @model_validator(mode="after")
    def _coherent(self) -> "PurgedDiagnostic":
        if self.n_bars < self.requested_folds:
            raise ValueError("purged bars must cover requested folds")
        # ADR-347 readers precede producer adoption; existing defaults stay shifted-only.
        is_high = self.method == HIGH_PURGED_METHOD
        if is_high:
            if (
                self.status == "unsupported"
                or self.dependency_rule != "rolling-high-v1"
                or self.max_price_lag not in (126, 189, 252)
            ):
                raise ValueError("high purged method requires its supported rule and shipped lag")
        elif self.method == ALPHA9_PURGED_METHOD:
            if (
                self.status == "unsupported"
                or self.dependency_rule != "rolling-alpha9-v1"
                or self.max_price_lag not in (4, 6, 11)
            ):
                raise ValueError("Alpha9 purged method requires its supported rule and shipped lag")
        elif self.dependency_rule in ("rolling-high-v1", "rolling-alpha9-v1"):
            raise ValueError("rolling dependency requires its attributed method")
        support = (self.dependency_rule, self.max_price_lag, self.embargo, self.kept_fold_ordinals)
        scores = (self.mean_oos_sharpe, self.mean_oos_hold_sharpe)
        if self.status == "unsupported":
            if self.reason is None or any(v is not None for v in (*support, *scores)):
                raise ValueError("unsupported purged evidence requires only its reason")
            return self
        if self.reason is not None or any(v is None for v in support):
            raise ValueError("supported purged evidence requires complete dependency geometry")
        assert self.max_price_lag is not None and self.embargo is not None
        assert self.kept_fold_ordinals is not None
        if self.embargo != max(self.floor, self.max_price_lag):
            raise ValueError("purged embargo must equal max(floor, allocated price lag)")
        prefix, suffix, count = kept_geometry(self.n_bars, self.requested_folds, self.embargo)
        if len(self.kept_fold_ordinals) != count:
            raise ValueError("kept fold cardinality contradicts geometry")
        previous = -1
        for j in self.kept_fold_ordinals:
            if j <= previous or j >= self.requested_folds or not (j < prefix or j >= suffix):
                raise ValueError("kept fold identities contradict geometry")
            previous = j
        if self.status == "measured":
            if not count or any(v is None for v in scores):
                raise ValueError("measured purged evidence requires kept folds and paired scores")
        elif count or any(v is not None for v in scores):
            raise ValueError("no usable folds requires empty geometry and absent scores")
        return self


def support_lag(
    strategy: CrossSectionalStrategy,
    configs: Sequence[tuple[Params, float]],
    prices: pd.DataFrame,
    *,
    runtime: HighRuntime | None = None,
) -> tuple[int | None, Reason | None]:
    """Audit exact factory/domain identity before direct operand bounds (ADR-325)."""
    known = {
        "xs_52w_high": (high_proximity_factory, (126, 189, 252)),
        "xs_alpha9": (alpha9_factory, (3, 5, 10)),
        "xs_momentum": (momentum_factory, (126, 189, 252)),
        "xs_reversal": (reversal_factory, (3, 5, 10)),
        "xs_short_term_reversal_1m": (short_term_reversal_factory, (21, 42, 63)),
    }
    entry = known.get(strategy.name)
    if entry is None or strategy.build is not entry[0]:
        return None, "unsupported_factory"
    if any(
        not isinstance(dtype, np.dtype) or dtype != np.dtype("float64") for dtype in prices.dtypes
    ):
        return None, "unsupported_price_dtype"
    lags = []
    for params, _ in configs:
        keys = (
            {"window"}
            if strategy.name in ("xs_52w_high", "xs_alpha9")
            else {"lookback", "skip"}
            if strategy.name == "xs_momentum"
            else {"lookback"}
        )
        if set(params) != keys or any(
            isinstance(v, (bool, np.bool_)) or not isinstance(v, Integral) for v in params.values()
        ):
            return None, "unsupported_parameters"
        window_key = "window" if strategy.name in ("xs_52w_high", "xs_alpha9") else "lookback"
        if params[window_key] not in entry[1] or (
            strategy.name == "xs_momentum" and params["skip"] not in (0, 21)
        ):
            return None, "unsupported_parameters"
        lags.append(
            int(params["window"])
            if strategy.name == "xs_52w_high"
            else int(params["window"]) + 1
            if strategy.name == "xs_alpha9"
            else int(params["lookback"]) + int(params.get("skip", 0)) + 1
        )
    if lags and strategy.name in ("xs_52w_high", "xs_alpha9"):
        observed = capture_high_runtime() if runtime is None else runtime
        if observed.version != "3.0.6":
            return None, "unsupported_pandas_version"
        if observed.use_numba is not False:
            return None, "unsupported_rolling_engine"
    return (max(lags), None) if lags else (None, "unsupported_parameters")


def _validate_sources(
    matrix: npt.NDArray[np.float64], benchmark: npt.NDArray[np.float64], n_bars: int
) -> None:
    for source in (matrix, benchmark):
        if np.ma.isMaskedArray(source) and np.any(np.ma.getmaskarray(source)):
            raise ValueError("purged source returns must be complete and finite")
        if source.dtype.kind not in "iuf" or not np.isfinite(source).all():
            raise ValueError("purged source returns must be real finite numeric values")
    if matrix.ndim != 2 or matrix.shape[0] != n_bars or matrix.shape[1] < 2:
        raise ValueError("purged matrix must carry all rows and >=2 configurations")
    if benchmark.shape != (n_bars,):
        raise ValueError("purged benchmark must carry every search row")


def measure_family_purged(
    strategy: CrossSectionalStrategy,
    configs: Sequence[tuple[Params, float]],
    prices: pd.DataFrame,
    matrix: npt.NDArray[np.float64],
    benchmark: npt.NDArray[np.float64],
    *,
    floor: int,
    requested_folds: int,
    high_runtime: HighRuntime | None = None,
) -> tuple[PurgedDiagnostic, PurgedCVResult | None]:
    """Use existing rows/evaluator; geometry insufficiency alone is an unmeasured outcome."""
    floor = require_trial_count(floor, minimum=0, parameter="embargo")
    requested_folds = requested_fold_count(requested_folds)
    _validate_sources(matrix, benchmark, len(prices))
    if matrix.shape[1] != len(configs):
        raise ValueError("purged matrix must retain every allocated config in order")
    is_high = strategy.name == "xs_52w_high" and strategy.build is high_proximity_factory
    is_alpha9 = strategy.name == "xs_alpha9" and strategy.build is alpha9_factory
    if is_high and high_runtime is None:
        raise ValueError("high purged measurement requires its matrix runtime receipt")
    if is_alpha9 and high_runtime is None:
        raise ValueError("Alpha9 purged measurement requires its matrix runtime receipt")
    lag, reason = support_lag(strategy, configs, prices, runtime=high_runtime)
    if lag is None:
        return PurgedDiagnostic(
            status="unsupported",
            n_bars=len(prices),
            requested_folds=requested_folds,
            floor=floor,
            reason=reason,
        ), None
    if (
        not prices.index.is_unique
        or not prices.index.is_monotonic_increasing
        or not prices.columns.is_unique
    ):
        raise ValueError("purged prices require unique ascending rows and unique columns")
    if (
        prices.isna().any().any()
        or not np.isfinite(prices.to_numpy()).all()
        or (prices <= 0).any().any()
    ):
        raise ValueError("purged prices must be complete finite positive observations")
    embargo = max(floor, lag)
    rule: Rule = (
        "rolling-high-v1"
        if is_high
        else "rolling-alpha9-v1"
        if is_alpha9
        else "shifted-momentum-v1"
        if strategy.name == "xs_momentum"
        else "shifted-reversal-v1"
    )
    method: Literal[
        "restricted-shift-family-purged-equal-weight-continuation-v1",
        "restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2",
        "restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3",
    ] = (
        HIGH_PURGED_METHOD
        if is_high
        else ALPHA9_PURGED_METHOD
        if is_alpha9
        else "restricted-shift-family-purged-equal-weight-continuation-v1"
    )
    _, _, count = kept_geometry(len(prices), requested_folds, embargo)
    if not count:
        return PurgedDiagnostic(
            method=method,
            status="no_usable_folds",
            n_bars=len(prices),
            requested_folds=requested_folds,
            floor=floor,
            dependency_rule=rule,
            max_price_lag=lag,
            embargo=embargo,
            kept_fold_ordinals=(),
        ), None
    splits = purged_kfold_splits(len(prices), requested_folds, embargo)
    kept = tuple(j for j, (train, test) in enumerate(splits) if len(train) and len(test))
    result = purged_cv_evaluate(matrix, splits, embargo=embargo, benchmark=benchmark)
    if result.n_folds != count or result.mean_oos_hold_sharpe is None:
        raise ValueError("purged measurement requires actual kept geometry and paired benchmark")
    return PurgedDiagnostic(
        method=method,
        status="measured",
        n_bars=len(prices),
        requested_folds=requested_folds,
        floor=floor,
        dependency_rule=rule,
        max_price_lag=lag,
        embargo=embargo,
        kept_fold_ordinals=kept,
        mean_oos_sharpe=result.mean_oos_sharpe,
        mean_oos_hold_sharpe=result.mean_oos_hold_sharpe,
    ), result
