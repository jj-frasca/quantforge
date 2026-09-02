"""Replicated whole-panel null artifact contracts (ADR-081).

This module contains identity, deterministic joint-row generation, and consolidation. Inference
and the manual sole-writer workflow build on these contracts without being able to reinterpret a
partial symbol shard as an independent panel observation.
"""

from collections.abc import Mapping, Sequence
from datetime import date
from hashlib import sha256
from math import isfinite

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")
_GENERATED_START = "2010-01-04"


class PanelSymbolExcess(BaseModel):
    """The frozen real-side value for one equally weighted cohort symbol."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    symbol: str = Field(min_length=1)
    walk_forward: float
    purged_cv: float | None = None


class PanelNullCohort(BaseModel):
    """Every input that identifies the real cohort and its jointly resampled source panel."""

    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...]
    symbol_excesses: tuple[PanelSymbolExcess, ...]
    source_start: date
    source_end: date
    source_sha256: str
    target_n_bars: int = Field(gt=0)
    history_tolerance: float = Field(ge=0.0, lt=1.0)
    search_config_version: str = Field(min_length=1)
    gate_config_version: str = Field(min_length=1)
    generator_version: str = Field(min_length=1)
    diagnostic_version: str = Field(min_length=1)
    base_seed: int = Field(ge=0)
    n_replicates: int = Field(gt=0)
    min_successful_symbols: int = Field(gt=0)

    @field_validator("source_sha256")
    @classmethod
    def _valid_source_digest(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("source_sha256 must be a lowercase hexadecimal SHA-256 digest")
        return value

    @model_validator(mode="after")
    def _validate_identity(self) -> "PanelNullCohort":
        if not self.symbols:
            raise ValueError("cohort must contain at least one symbol")
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("cohort contains a duplicate symbol")
        measured_symbols = tuple(value.symbol for value in self.symbol_excesses)
        if measured_symbols != self.symbols:
            raise ValueError("symbol_excesses must match the ordered symbols exactly")
        if any(
            not isfinite(value.walk_forward)
            or (value.purged_cv is not None and not isfinite(value.purged_cv))
            for value in self.symbol_excesses
        ):
            raise ValueError("symbol excess statistics must be finite")
        if self.min_successful_symbols > len(self.symbols):
            raise ValueError("min_successful_symbols cannot exceed the frozen cohort size")
        if self.source_end < self.source_start:
            raise ValueError("source_end must not precede source_start")
        return self


class PanelNullError(BaseModel):
    """One failed symbol search retained inside its indivisible panel replicate."""

    model_config = ConfigDict(frozen=True)

    symbol: str = Field(min_length=1)
    message: str = Field(min_length=1)


class PanelNullReplicate(BaseModel):
    """One independent draw of the complete panel statistic, never a symbol shard."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    panel_index: int = Field(ge=0)
    panel_id: str = Field(min_length=1)
    seed: int = Field(ge=0)
    successful_symbols: int = Field(ge=0)
    errors: tuple[PanelNullError, ...] = ()
    walk_forward_excess: float
    purged_cv_excess: float | None = None


class PanelNullShard(BaseModel):
    """A batch of complete global panel indices sharing one exact cohort identity."""

    model_config = ConfigDict(frozen=True)

    cohort: PanelNullCohort
    replicates: tuple[PanelNullReplicate, ...]


class PanelNullCalibration(BaseModel):
    """The deterministic consolidation product for one fixed ADR-081 measurement."""

    model_config = ConfigDict(frozen=True)

    cohort: PanelNullCohort
    replicates: tuple[PanelNullReplicate, ...]

    @model_validator(mode="after")
    def _validate_complete_measurement(self) -> "PanelNullCalibration":
        _validate_complete_replicates(self.cohort, self.replicates)
        indices = tuple(replicate.panel_index for replicate in self.replicates)
        if indices != tuple(range(self.cohort.n_replicates)):
            raise ValueError("replicates must be ordered by panel index")
        return self


def panel_seed(base_seed: int, panel_index: int) -> int:
    """Derive a batching-invariant signed-64-bit seed from one global panel index."""
    if base_seed < 0:
        raise ValueError("base_seed must be non-negative")
    if panel_index < 0:
        raise ValueError("panel_index must be non-negative")
    digest = sha256(f"{base_seed}:{panel_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def joint_iid_panel_null(
    source_panel: Mapping[str, pd.DataFrame],
    n_bars: int,
    *,
    seed: int,
) -> dict[str, pd.DataFrame]:
    """Jointly resample complete calendar rows and reconstruct every symbol's OHLCV path.

    The caller supplies the already aligned, complete source panel frozen by ADR-081. One iid row
    draw is shared across symbols, preserving contemporaneous dependence while destroying calendar
    order. Each selected row carries its close return and same-bar OHLCV geometry together.
    """
    if n_bars < 1:
        raise ValueError("n_bars must be >= 1")
    if not source_panel:
        raise ValueError("source panel must contain at least one symbol")

    frames = list(source_panel.items())
    reference_index = frames[0][1].index
    if len(reference_index) < 2:
        raise ValueError("source panel needs at least two aligned rows")
    if not isinstance(reference_index, pd.DatetimeIndex) or reference_index.tz is None:
        raise ValueError("source panel calendar index must be timezone-aware")

    for symbol, frame in frames:
        missing = set(_OHLCV_COLUMNS).difference(frame.columns)
        if missing:
            raise ValueError(f"source panel symbol {symbol} is missing OHLCV columns")
        if not frame.index.equals(reference_index):
            raise ValueError("source panel symbols must have exactly aligned calendar rows")
        if not reference_index.is_monotonic_increasing or not reference_index.is_unique:
            raise ValueError("source panel calendar rows must be ordered and unique")
        values = frame.loc[:, _OHLCV_COLUMNS].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError("source panel OHLCV values must be finite")
        if (frame.loc[:, ("open", "high", "low", "close")] <= 0).any().any():
            raise ValueError("source panel prices must be positive")
        if (frame["volume"] < 0).any():
            raise ValueError("source panel volume must be non-negative")
        if (frame["high"] < frame.loc[:, ("open", "close")].max(axis=1)).any() or (
            frame["low"] > frame.loc[:, ("open", "close")].min(axis=1)
        ).any():
            raise ValueError("source panel must have valid OHLCV geometry")

    rng = np.random.default_rng(seed)
    draw = rng.integers(0, len(reference_index) - 1, n_bars)
    generated_index = pd.date_range(_GENERATED_START, periods=n_bars, freq="B", tz="UTC")
    generated: dict[str, pd.DataFrame] = {}
    for symbol, frame in frames:
        returns = frame["close"].pct_change().iloc[1:].to_numpy()
        if not np.isfinite(returns).all() or (returns <= -1.0).any():
            raise ValueError("source panel close returns must be finite and greater than -1")
        bars = frame.iloc[1:]
        closes = float(frame["close"].iloc[0]) * np.cumprod(1.0 + returns[draw])
        generated[symbol] = pd.DataFrame(
            {
                "open": closes * (bars["open"] / bars["close"]).to_numpy()[draw],
                "high": closes * (bars["high"] / bars["close"]).to_numpy()[draw],
                "low": closes * (bars["low"] / bars["close"]).to_numpy()[draw],
                "close": closes,
                "volume": bars["volume"].to_numpy()[draw],
            },
            index=generated_index,
        ).loc[:, _OHLCV_COLUMNS]
    return generated


def _validate_complete_replicates(
    cohort: PanelNullCohort,
    replicates: Sequence[PanelNullReplicate],
) -> None:
    if any(
        not isfinite(value.walk_forward)
        or (value.purged_cv is not None and not isfinite(value.purged_cv))
        for value in cohort.symbol_excesses
    ):
        raise ValueError("symbol excess statistics must be finite")
    indices = [replicate.panel_index for replicate in replicates]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate panel index")
    if set(indices) != set(range(cohort.n_replicates)):
        raise ValueError("shards must contain the complete panel indices")
    if any(
        replicate.seed != panel_seed(cohort.base_seed, replicate.panel_index)
        for replicate in replicates
    ):
        raise ValueError("replicate seed does not match the derived seed")

    panel_ids = [replicate.panel_id for replicate in replicates]
    if len(set(panel_ids)) != len(panel_ids):
        raise ValueError("duplicate panel id")
    cohort_symbols = set(cohort.symbols)
    for replicate in replicates:
        if not isfinite(replicate.walk_forward_excess) or (
            replicate.purged_cv_excess is not None and not isfinite(replicate.purged_cv_excess)
        ):
            raise ValueError("replicate statistics must be finite")
        error_symbols = [error.symbol for error in replicate.errors]
        if len(set(error_symbols)) != len(error_symbols):
            raise ValueError("replicate contains a duplicate error symbol")
        if any(symbol not in cohort_symbols for symbol in error_symbols):
            raise ValueError("replicate contains an error symbol outside the frozen cohort")
        if replicate.successful_symbols < cohort.min_successful_symbols:
            raise ValueError("replicate is below the successful-symbol floor")
        if replicate.successful_symbols + len(replicate.errors) != len(cohort.symbols):
            raise ValueError("replicate must account for every cohort symbol")


def merge_panel_null_shards(
    shards: Sequence[PanelNullShard],
) -> PanelNullCalibration:
    """Merge only complete panel units and reject every identity or index ambiguity."""
    if not shards:
        raise ValueError("at least one shard is required")

    cohort = shards[0].cohort
    if any(shard.cohort != cohort for shard in shards[1:]):
        raise ValueError("all shards must share the same cohort identity")

    replicates = [replicate for shard in shards for replicate in shard.replicates]
    _validate_complete_replicates(cohort, replicates)

    ordered = tuple(sorted(replicates, key=lambda replicate: replicate.panel_index))
    return PanelNullCalibration(cohort=cohort, replicates=ordered)
