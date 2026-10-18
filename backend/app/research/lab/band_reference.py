"""ADR313 declared nominal binary64 band sign reference; never source certification."""

from collections.abc import Mapping
from math import isfinite
from numbers import Real
from typing import Annotated, Literal, NamedTuple

import numpy as np
import pandas as pd
from pydantic import BaseModel, BeforeValidator, ConfigDict

from app.research.frames import copy_frame
from app.research.lab.band_posterior import band_price_posterior


def _scalar(value: object) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, Real)
        or value != value
        or value == float("inf")
        or value == -float("inf")
    ):
        raise ValueError("band law requires original finite nonboolean Real scalars")
    try:
        result = float(value)
    except (OverflowError, ValueError, TypeError) as exc:
        raise ValueError("band law must be float-representable") from exc
    if not isfinite(result):
        raise ValueError("band law must be finite")
    return result


def _positive(value: object) -> float:
    result = _scalar(value)
    if value <= 0 or result <= 0:  # type: ignore[operator]
        raise ValueError("band law requires positive original and normalized scalars")
    return result


def _share(value: object) -> float:
    result = _positive(value)
    if value > 1 or result > 1 or (value < 1 and result == 1):  # type: ignore[operator]
        raise ValueError("band deviation share must preserve (0, 1] and positive level noise")
    return result


class BandReference(BaseModel):
    """Explicit nominal Gaussian law and fixed sign arithmetic, not provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid", revalidate_instances="always")
    method: Literal["band_conditional_simple_mean_sign_zero_start_v1"]
    drift: Annotated[float, BeforeValidator(_scalar)]
    total_vol: Annotated[float, BeforeValidator(_positive)]
    start_price: Annotated[float, BeforeValidator(_positive)]


class BandReferenceLaw(NamedTuple):
    half_life: float
    deviation_share: float
    rho: float
    level_vol: float
    deviation_vol: float


def band_reference_description(reference: BandReference | None) -> str:
    if reference is None:
        return "unknown (historical or externally supplied reference)"
    return (
        f"{reference.method}; drift={reference.drift}; total_vol={reference.total_vol}; "
        f"start_price={reference.start_price}; nominal Gaussian law"
    )


def band_reference_law(
    reference: BandReference, *, half_life: object, deviation_share: object
) -> BandReferenceLaw:
    reference = BandReference.model_validate(reference)
    h, share = _positive(half_life), _share(deviation_share)
    try:
        with np.errstate(all="ignore"):
            inverse = 1.0 / h
            rho = 0.5**inverse
            denominator = 2.0 * (1.0 - rho)
            ratio = share / denominator
            deviation_vol = float(reference.total_vol * np.sqrt(ratio))
            level_vol = float(reference.total_vol * np.sqrt(1.0 - share))
            if not all(
                isfinite(x) for x in (inverse, rho, denominator, ratio, deviation_vol, level_vol)
            ):
                raise ValueError("band derived law must be finite")
            if not 0 <= rho < 1 or deviation_vol <= 0 or (share < 1 and level_vol <= 0):
                raise ValueError("band derived law loses positive noise or stationarity")
            band_price_posterior(
                np.array([], dtype=float),
                rho=rho,
                level_vol=level_vol,
                deviation_vol=deviation_vol,
                drift=reference.drift,
                start_price=reference.start_price,
            )
    except (OverflowError, FloatingPointError, ZeroDivisionError) as exc:
        raise ValueError("band derived law must remain measurable") from exc
    return BandReferenceLaw(h, share, rho, level_vol, deviation_vol)


def band_reference_sign_score(mean: float, variance: float) -> float:
    if not isfinite(mean) or not isfinite(variance) or variance <= 0:
        raise ValueError("band predictions require finite mean and positive variance")
    doubled = 2.0 * mean
    score = doubled + variance
    if not isfinite(doubled) or not isfinite(score):
        raise ValueError("band sign arithmetic must remain finite")
    return score


def _values(series: pd.Series, *, positive: bool = False) -> np.ndarray:
    original = series.to_numpy()
    if original.dtype.kind not in "iuf" or (
        np.ma.isMaskedArray(original) and np.any(np.ma.getmaskarray(original))
    ):
        raise ValueError("band source requires original complete real numeric evidence")
    if not np.isfinite(original).all() or (positive and (original <= 0).any()):
        raise ValueError("band source must be finite and closes positive")
    with np.errstate(all="ignore"):
        values = np.array(original, dtype=np.float64, copy=True)
    if not np.isfinite(values).all() or (positive and (values <= 0).any()):
        raise ValueError("normalized band source must remain finite and closes positive")
    return values


def band_reference_preflight(
    frames: Mapping[str, pd.DataFrame],
    deviations: Mapping[str, pd.Series],
    reference: BandReference,
    law: BandReferenceLaw,
) -> tuple[dict[str, pd.DataFrame], dict[str, tuple[pd.Series, pd.Series]]]:
    """Own all predictions before scoring; numeric NumPy-backed columns only."""
    if set(frames) != set(deviations):
        raise ValueError("band source and deviation keys must match exactly")
    owned: dict[str, pd.DataFrame] = {}
    predictions: dict[str, tuple[pd.Series, pd.Series]] = {}
    delta = law.rho - 1.0
    delta_square = delta * delta
    q = (law.deviation_vol * law.deviation_vol) * (1.0 - law.rho * law.rho)
    noise = law.level_vol * law.level_vol
    base = q + noise
    for symbol, frame in frames.items():
        if (
            not frame.index.is_unique
            or not frame.index.is_monotonic_increasing
            or not frame.index.equals(deviations[symbol].index)
        ):
            raise ValueError("band sources require exact unique ascending matching indexes")
        if not frame.columns.is_unique or "close" not in frame.columns:
            raise ValueError("band frames require unique columns and close evidence")
        snapshot = copy_frame(frame)
        for column in snapshot.columns:
            snapshot[column] = _values(frame[column], positive=column == "close")
        closes = _values(frame["close"], positive=True)
        states = _values(deviations[symbol])
        with np.errstate(all="ignore"):
            logs = np.log(closes)
            returns = closes[1:] / closes[:-1] - 1.0
        if not np.isfinite(logs).all() or not np.isfinite(returns).all():
            raise ValueError("band logs and returns must remain finite")
        posterior = band_price_posterior(
            logs,
            rho=law.rho,
            level_vol=law.level_vol,
            deviation_vol=law.deviation_vol,
            drift=reference.drift,
            start_price=reference.start_price,
        )
        latent = np.full(len(closes), np.nan)
        observed = np.full(len(closes), np.nan)
        for i in range(1, len(closes)):
            for state, variance, target in (
                (states[i - 1], 0.0, latent),
                (posterior.deviation_mean[i - 1], posterior.deviation_variance[i - 1], observed),
            ):
                product = delta * float(state)
                mean = reference.drift + product
                component = delta_square * float(variance)
                total = base + component
                if not all(
                    isfinite(x) for x in (delta, delta_square, product, mean, component, total)
                ) or (variance > 0 and component == 0):
                    raise ValueError("band prediction arithmetic loses measurable evidence")
                target[i] = band_reference_sign_score(mean, total)
        owned[symbol] = snapshot
        predictions[symbol] = (
            pd.Series(latent, index=snapshot.index),
            pd.Series(observed, index=snapshot.index),
        )
    return owned, predictions
