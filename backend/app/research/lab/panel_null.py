"""Replicated whole-panel null artifact contracts (ADR-081).

This module contains identity, deterministic joint-row generation, consolidation, and the fixed
tail inference. The manual sole-writer workflow builds on these contracts without being able to
reinterpret a partial symbol shard as an independent panel observation.
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from scipy.stats import beta

from app.research.lab.experiment import Experiment, selected_trial
from app.research.lab.gate import GateConfig

_OHLCV_COLUMNS = ("open", "high", "low", "close", "volume")
_SOURCE_ARCHIVE_VERSION = "quantforge-panel-null-source-archive-v1"
_SOURCE_ARCHIVE_FIELDS = frozenset(
    {"format_version", "symbols", "timestamps_ns", "ohlcv", "source_sha256"}
)
_GENERATED_START = "2010-01-04"
_PANEL_REPLICATES = 400
_TAIL_THRESHOLD = 0.025
_TAIL_INTERVAL_CONFIDENCE = 0.975
_SIMULTANEOUS_CONFIDENCE = 0.95


@dataclass(frozen=True)
class PreparedPanelNullSource:
    """One copied, complete, canonically identified source panel."""

    symbols: tuple[str, ...]
    target_n_bars: int
    source_start: date
    source_end: date
    source_sha256: str
    _frames: tuple[tuple[str, pd.DataFrame], ...] = dataclass_field(repr=False, compare=False)

    def __post_init__(self) -> None:
        copied = tuple((symbol, frame.copy(deep=True)) for symbol, frame in self._frames)
        object.__setattr__(self, "_frames", copied)
        if tuple(symbol for symbol, _ in copied) != self.symbols:
            raise ValueError("prepared source frames must match the ordered symbols")
        if self.target_n_bars < 2 or any(len(frame) != self.target_n_bars for _, frame in copied):
            raise ValueError("prepared source frames must match target_n_bars")
        _validate_prepared_source_frames(copied)
        reference_index = copied[0][1].index
        if (reference_index[0].date(), reference_index[-1].date()) != (
            self.source_start,
            self.source_end,
        ):
            raise ValueError("prepared source calendar range does not match its frames")
        if _digest_source_panel(copied) != self.source_sha256:
            raise ValueError("prepared source digest does not match its frames")

    def to_frames(self) -> dict[str, pd.DataFrame]:
        """Return defensive copies in the frozen cohort order."""
        return {symbol: frame.copy(deep=True) for symbol, frame in self._frames}


class PanelSymbolExcess(BaseModel):
    """The frozen real-side value for one equally weighted cohort symbol."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    symbol: str = Field(min_length=1)
    walk_forward: float
    purged_cv: float | None = None


class SelectedPanelNullCohort(BaseModel):
    """The pre-source-fetch real cohort and its equal-symbol excess estimand."""

    model_config = ConfigDict(frozen=True)

    symbols: tuple[str, ...]
    symbol_excesses: tuple[PanelSymbolExcess, ...]
    target_n_bars: int = Field(gt=0)
    history_tolerance: float = Field(ge=0.0, lt=1.0)
    search_config_version: str = Field(min_length=1)
    gate_config_version: str = Field(min_length=1)
    min_symbols: int = Field(gt=0)

    @model_validator(mode="after")
    def _validate_selection(self) -> "SelectedPanelNullCohort":
        if len(self.symbols) < self.min_symbols:
            raise ValueError(
                f"only {len(self.symbols)} measured symbols; selection requires {self.min_symbols}"
            )
        if self.symbols != tuple(sorted(self.symbols)):
            raise ValueError("selected cohort symbols must be in canonical order")
        if len(set(self.symbols)) != len(self.symbols):
            raise ValueError("selected cohort contains a duplicate symbol")
        if tuple(value.symbol for value in self.symbol_excesses) != self.symbols:
            raise ValueError("symbol excesses must match the selected symbols")
        return self


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

    @model_validator(mode="after")
    def _validate_partial_measurement(self) -> "PanelNullShard":
        _validate_shard_replicates(self.cohort, self.replicates)
        return self


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


class BinomialConfidenceInterval(BaseModel):
    """One exact interval for a panel-level tail probability."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    low: float = Field(ge=0.0, le=1.0)
    high: float = Field(ge=0.0, le=1.0)


class PanelDiagnosticInference(BaseModel):
    """The pre-registered ADR-081/082 reading for one panel diagnostic."""

    model_config = ConfigDict(frozen=True, allow_inf_nan=False)

    diagnostic: Literal["walk_forward", "purged_cv"]
    real_statistic: float
    null_median: float
    null_p025: float
    null_p975: float
    n_replicates: int = Field(gt=0)
    lower_tail_count: int = Field(ge=0)
    upper_tail_count: int = Field(ge=0)
    two_sided_p_value: float = Field(ge=0.0, le=1.0)
    lower_tail_interval: BinomialConfidenceInterval
    upper_tail_interval: BinomialConfidenceInterval
    tail_interval_confidence: float = Field(
        default=_TAIL_INTERVAL_CONFIDENCE,
        ge=_TAIL_INTERVAL_CONFIDENCE,
        le=_TAIL_INTERVAL_CONFIDENCE,
    )
    simultaneous_confidence: float = Field(
        default=_SIMULTANEOUS_CONFIDENCE, ge=_SIMULTANEOUS_CONFIDENCE, le=_SIMULTANEOUS_CONFIDENCE
    )
    resolution: Literal["separated_below", "separated_above", "not_separated", "unresolved"]


class PanelNullInference(BaseModel):
    """Primary and optional secondary inference from one complete panel calibration."""

    model_config = ConfigDict(frozen=True)

    walk_forward: PanelDiagnosticInference
    purged_cv: PanelDiagnosticInference | None = None


def panel_seed(base_seed: int, panel_index: int) -> int:
    """Derive a batching-invariant signed-64-bit seed from one global panel index."""
    if base_seed < 0:
        raise ValueError("base_seed must be non-negative")
    if panel_index < 0:
        raise ValueError("panel_index must be non-negative")
    digest = sha256(f"{base_seed}:{panel_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


def select_panel_null_cohort(
    experiments: Sequence[Experiment],
    *,
    target_n_bars: int,
    history_tolerance: float,
    search_config_version: str,
    gate_config_version: str,
    min_symbols: int = 30,
) -> SelectedPanelNullCohort:
    """Freeze the matched real excess panel with one median-weighted value per symbol."""
    if target_n_bars < 1:
        raise ValueError("target_n_bars must be positive")
    if not 0.0 <= history_tolerance < 1.0:
        raise ValueError("history_tolerance must be in [0, 1)")
    if not search_config_version or not gate_config_version:
        raise ValueError("search and gate config versions must be non-empty")
    if min_symbols < 1:
        raise ValueError("min_symbols must be positive")

    matched = [
        experiment
        for experiment in experiments
        if experiment.n_bars is not None
        and abs(experiment.n_bars - target_n_bars) <= history_tolerance * target_n_bars
        and experiment.search_config_version == search_config_version
        and experiment.gate_config.version_hash == gate_config_version
    ]
    experiment_ids = [experiment.experiment_id for experiment in matched]
    if len(set(experiment_ids)) != len(experiment_ids):
        raise ValueError("matched cohort contains a duplicate experiment id")

    walk_forward_by_symbol: dict[str, list[float]] = {}
    purged_cv_by_symbol: dict[str, list[float]] = {}
    for experiment in matched:
        finalist = selected_trial(experiment)
        if finalist.walk_forward_oos_sharpe is None or experiment.walk_forward_hold_sharpe is None:
            continue
        walk_forward_by_symbol.setdefault(experiment.symbol, []).append(
            finalist.walk_forward_oos_sharpe - experiment.walk_forward_hold_sharpe
        )
        if (
            finalist.purged_cv_oos_sharpe is not None
            and experiment.purged_cv_hold_sharpe is not None
        ):
            purged_cv_by_symbol.setdefault(experiment.symbol, []).append(
                finalist.purged_cv_oos_sharpe - experiment.purged_cv_hold_sharpe
            )

    symbols = tuple(sorted(walk_forward_by_symbol))
    symbol_excesses = tuple(
        PanelSymbolExcess(
            symbol=symbol,
            walk_forward=float(np.median(walk_forward_by_symbol[symbol])),
            purged_cv=(
                float(np.median(purged_cv_by_symbol[symbol]))
                if symbol in purged_cv_by_symbol
                else None
            ),
        )
        for symbol in symbols
    )
    return SelectedPanelNullCohort(
        symbols=symbols,
        symbol_excesses=symbol_excesses,
        target_n_bars=target_n_bars,
        history_tolerance=history_tolerance,
        search_config_version=search_config_version,
        gate_config_version=gate_config_version,
        min_symbols=min_symbols,
    )


def _digest_source_panel(frames: Sequence[tuple[str, pd.DataFrame]]) -> str:
    digest = sha256(b"quantforge-panel-null-source-v1\0")

    def update_length_prefixed(payload: bytes) -> None:
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)

    update_length_prefixed("\0".join(_OHLCV_COLUMNS).encode())
    for symbol, frame in frames:
        update_length_prefixed(symbol.encode())
        timestamps = np.asarray(frame.index.as_unit("ns").asi8, dtype=">i8").tobytes(order="C")
        values = np.asarray(frame.loc[:, _OHLCV_COLUMNS], dtype=">f8").tobytes(order="C")
        update_length_prefixed(timestamps)
        update_length_prefixed(values)
    return digest.hexdigest()


def _validate_prepared_source_frames(frames: Sequence[tuple[str, pd.DataFrame]]) -> None:
    if not frames:
        raise ValueError("prepared source must contain at least one frame")
    reference_index = frames[0][1].index
    if not isinstance(reference_index, pd.DatetimeIndex) or reference_index.tz is None:
        raise ValueError("prepared source calendar index must be timezone-aware")
    if str(reference_index.tz) != "UTC":
        raise ValueError("prepared source calendar index must be UTC")
    if not reference_index.is_monotonic_increasing or not reference_index.is_unique:
        raise ValueError("prepared source calendar rows must be ordered and unique")

    for symbol, frame in frames:
        if tuple(frame.columns) != _OHLCV_COLUMNS:
            raise ValueError(
                f"prepared source symbol {symbol} must contain canonical OHLCV columns"
            )
        if not frame.index.equals(reference_index):
            raise ValueError("prepared source symbols must have exactly aligned calendar rows")
        values = frame.to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise ValueError(f"prepared source symbol {symbol} contains non-finite OHLCV values")
        if (frame.loc[:, ("open", "high", "low", "close")] <= 0).any().any():
            raise ValueError(f"prepared source symbol {symbol} contains non-positive prices")
        if (frame["volume"] < 0).any():
            raise ValueError(f"prepared source symbol {symbol} contains negative volume")
        if (frame["high"] < frame.loc[:, ("open", "close")].max(axis=1)).any() or (
            frame["low"] > frame.loc[:, ("open", "close")].min(axis=1)
        ).any():
            raise ValueError(f"prepared source symbol {symbol} has invalid OHLCV geometry")


def prepare_panel_null_source(
    source_panel: Mapping[str, pd.DataFrame],
    symbols: Sequence[str],
    *,
    target_n_bars: int,
) -> PreparedPanelNullSource:
    """Freeze the ordered complete-case calendar and canonical source digest."""
    ordered_symbols = tuple(symbols)
    if not ordered_symbols:
        raise ValueError("cohort must contain at least one symbol")
    if len(set(ordered_symbols)) != len(ordered_symbols):
        raise ValueError("cohort contains a duplicate symbol")
    if target_n_bars < 2:
        raise ValueError("target_n_bars must be >= 2")

    supplied = set(source_panel)
    requested = set(ordered_symbols)
    missing = sorted(requested - supplied)
    unexpected = sorted(supplied - requested)
    if missing:
        raise ValueError(f"source panel is missing symbols: {', '.join(missing)}")
    if unexpected:
        raise ValueError(f"source panel contains unexpected symbols: {', '.join(unexpected)}")

    normalized: list[tuple[str, pd.DataFrame]] = []
    common_index: pd.DatetimeIndex | None = None
    for symbol in ordered_symbols:
        frame = source_panel[symbol]
        missing_columns = set(_OHLCV_COLUMNS).difference(frame.columns)
        if missing_columns:
            raise ValueError(f"source panel symbol {symbol} is missing OHLCV columns")
        if not isinstance(frame.index, pd.DatetimeIndex) or frame.index.tz is None:
            raise ValueError("source panel calendar index must be timezone-aware")
        if not frame.index.is_monotonic_increasing or not frame.index.is_unique:
            raise ValueError("source panel calendar rows must be ordered and unique")

        selected = frame.loc[:, _OHLCV_COLUMNS].astype(np.float64).copy(deep=True)
        selected.index = selected.index.tz_convert("UTC").as_unit("ns")
        normalized.append((symbol, selected))
        common_index = (
            selected.index
            if common_index is None
            else common_index.intersection(selected.index, sort=False)
        )

    assert common_index is not None
    complete = np.ones(len(common_index), dtype=bool)
    for _, frame in normalized:
        complete &= frame.reindex(common_index).notna().all(axis=1).to_numpy()
    complete_index = common_index[complete]
    if len(complete_index) < target_n_bars:
        raise ValueError(
            f"complete calendar has {len(complete_index)} rows but requires {target_n_bars} "
            f"for symbols: {', '.join(ordered_symbols)}"
        )

    retained_index = complete_index[-target_n_bars:]
    retained = tuple(
        (symbol, frame.loc[retained_index].copy(deep=True)) for symbol, frame in normalized
    )
    return PreparedPanelNullSource(
        symbols=ordered_symbols,
        target_n_bars=target_n_bars,
        source_start=retained_index[0].date(),
        source_end=retained_index[-1].date(),
        source_sha256=_digest_source_panel(retained),
        _frames=retained,
    )


def save_prepared_panel_null_source(prepared: PreparedPanelNullSource, path: Path) -> None:
    """Write one immutable, pickle-free source archive without replacing an existing file."""
    prepared = _revalidate_prepared_source(prepared)
    frames = prepared.to_frames()
    reference_index = frames[prepared.symbols[0]].index
    values = np.stack(
        [
            frames[symbol].loc[:, _OHLCV_COLUMNS].to_numpy(dtype=np.float64)
            for symbol in prepared.symbols
        ]
    )
    with Path(path).open("xb") as archive_file:
        np.savez_compressed(
            archive_file,
            format_version=np.asarray(_SOURCE_ARCHIVE_VERSION),
            symbols=np.asarray(prepared.symbols, dtype=str),
            timestamps_ns=np.asarray(reference_index.as_unit("ns").asi8, dtype=np.int64),
            ohlcv=values,
            source_sha256=np.asarray(prepared.source_sha256),
        )


def load_prepared_panel_null_source(path: Path) -> PreparedPanelNullSource:
    """Load and revalidate one exact prepared source archive."""
    with np.load(Path(path), allow_pickle=False) as archive:
        if set(archive.files) != _SOURCE_ARCHIVE_FIELDS:
            raise ValueError("prepared source archive fields do not match the required schema")
        format_version = archive["format_version"]
        symbols_array = archive["symbols"]
        timestamps_ns = archive["timestamps_ns"]
        values = archive["ohlcv"]
        source_digest = archive["source_sha256"]

        if format_version.ndim != 0 or str(format_version.item()) != _SOURCE_ARCHIVE_VERSION:
            raise ValueError("prepared source archive format version is unsupported")
        if symbols_array.ndim != 1 or symbols_array.dtype.kind != "U" or len(symbols_array) == 0:
            raise ValueError("prepared source archive symbols are invalid")
        symbols = tuple(str(symbol) for symbol in symbols_array.tolist())
        if any(not symbol for symbol in symbols) or len(set(symbols)) != len(symbols):
            raise ValueError("prepared source archive symbols are invalid")
        if timestamps_ns.ndim != 1 or timestamps_ns.dtype != np.dtype(np.int64):
            raise ValueError("prepared source archive timestamps are invalid")
        if len(timestamps_ns) < 2:
            raise ValueError("prepared source archive must contain at least two timestamps")
        if values.dtype != np.dtype(np.float64) or values.shape != (
            len(symbols),
            len(timestamps_ns),
            len(_OHLCV_COLUMNS),
        ):
            raise ValueError("prepared source archive OHLCV array has an invalid shape or dtype")
        if source_digest.ndim != 0 or source_digest.dtype.kind != "U":
            raise ValueError("prepared source archive digest is invalid")
        digest = str(source_digest.item())

        index = pd.DatetimeIndex(pd.to_datetime(timestamps_ns.copy(), unit="ns", utc=True))
        frames = tuple(
            (
                symbol,
                pd.DataFrame(values[position].copy(), index=index.copy(), columns=_OHLCV_COLUMNS),
            )
            for position, symbol in enumerate(symbols)
        )

    return PreparedPanelNullSource(
        symbols=symbols,
        target_n_bars=len(index),
        source_start=index[0].date(),
        source_end=index[-1].date(),
        source_sha256=digest,
        _frames=frames,
    )


def save_panel_null_shard(shard: PanelNullShard, path: Path) -> None:
    """Write one validated scratch shard without replacing an existing artifact."""
    validated = PanelNullShard.model_validate(shard.model_dump())
    with Path(path).open("x", encoding="utf-8") as shard_file:
        shard_file.write(validated.model_dump_json())
        shard_file.write("\n")


def save_panel_null_cohort(cohort: PanelNullCohort, path: Path) -> None:
    """Write one immutable cohort manifest without replacing an existing artifact."""
    validated = PanelNullCohort.model_validate(cohort.model_dump())
    with Path(path).open("x", encoding="utf-8") as cohort_file:
        cohort_file.write(validated.model_dump_json())
        cohort_file.write("\n")


def load_panel_null_cohort(path: Path) -> PanelNullCohort:
    """Load and revalidate one immutable cohort manifest."""
    return PanelNullCohort.model_validate_json(Path(path).read_text(encoding="utf-8"))


def load_panel_null_shard(path: Path) -> PanelNullShard:
    """Load and revalidate one scratch shard, including every complete panel unit."""
    return PanelNullShard.model_validate_json(Path(path).read_text(encoding="utf-8"))


def fetch_panel_null_source(
    selected: SelectedPanelNullCohort,
    fetch_frame: Callable[[str], pd.DataFrame],
) -> PreparedPanelNullSource:
    """Fetch every frozen symbol once, then prepare one exact complete-case panel."""
    selected = SelectedPanelNullCohort.model_validate(selected.model_dump())
    source_panel: dict[str, pd.DataFrame] = {}
    failures: list[str] = []
    for symbol in selected.symbols:
        try:
            source_panel[symbol] = fetch_frame(symbol)
        except Exception as error:
            failures.append(f"{symbol}: {error}")

    if failures:
        raise ValueError(f"source fetch failed for symbols: {'; '.join(failures)}")
    return prepare_panel_null_source(
        source_panel,
        selected.symbols,
        target_n_bars=selected.target_n_bars,
    )


def _revalidate_prepared_source(prepared: PreparedPanelNullSource) -> PreparedPanelNullSource:
    return PreparedPanelNullSource(
        symbols=prepared.symbols,
        target_n_bars=prepared.target_n_bars,
        source_start=prepared.source_start,
        source_end=prepared.source_end,
        source_sha256=prepared.source_sha256,
        _frames=tuple(prepared.to_frames().items()),
    )


def _require_prepared_cohort_identity(
    cohort: PanelNullCohort, prepared: PreparedPanelNullSource
) -> None:
    if cohort.symbols != prepared.symbols:
        raise ValueError("prepared source ordered symbols do not match the panel cohort")
    if cohort.target_n_bars != prepared.target_n_bars:
        raise ValueError("prepared source target history does not match the panel cohort")
    if (cohort.source_start, cohort.source_end) != (
        prepared.source_start,
        prepared.source_end,
    ):
        raise ValueError("prepared source calendar range does not match the panel cohort")
    if cohort.source_sha256 != prepared.source_sha256:
        raise ValueError("prepared source digest does not match the panel cohort")


def bind_panel_null_cohort(
    selected: SelectedPanelNullCohort,
    prepared: PreparedPanelNullSource,
    *,
    generator_version: str,
    diagnostic_version: str,
    base_seed: int,
) -> PanelNullCohort:
    """Bind the frozen real estimand to its exact prepared source-panel identity."""
    selected = SelectedPanelNullCohort.model_validate(selected.model_dump())
    prepared = _revalidate_prepared_source(prepared)
    if selected.symbols != prepared.symbols:
        raise ValueError("prepared source ordered symbols do not match the selected cohort")
    if selected.target_n_bars != prepared.target_n_bars:
        raise ValueError("prepared source target history does not match the selected cohort")

    return PanelNullCohort(
        symbols=selected.symbols,
        symbol_excesses=selected.symbol_excesses,
        source_start=prepared.source_start,
        source_end=prepared.source_end,
        source_sha256=prepared.source_sha256,
        target_n_bars=selected.target_n_bars,
        history_tolerance=selected.history_tolerance,
        search_config_version=selected.search_config_version,
        gate_config_version=selected.gate_config_version,
        generator_version=generator_version,
        diagnostic_version=diagnostic_version,
        base_seed=base_seed,
        n_replicates=_PANEL_REPLICATES,
        min_successful_symbols=selected.min_symbols,
    )


def make_production_panel_null_search(
    cohort: PanelNullCohort,
    strategy_names: Sequence[str],
    *,
    config: GateConfig,
    n_per_param: int = 3,
    refine: bool = True,
    refine_span: float = 0.25,
    select_by: Literal["observed", "walk_forward"] = "observed",
    run_search_fn: Callable[..., Experiment] | None = None,
) -> Callable[[pd.DataFrame, str], Experiment]:
    """Pin production search inputs to the frozen cohort before expensive execution."""
    from app.research.lab.calibration import calibration_search_version
    from app.research.lab.search import run_search

    cohort = PanelNullCohort.model_validate(cohort.model_dump())
    strategies = list(strategy_names)
    search_version = calibration_search_version(
        strategies,
        n_per_param=n_per_param,
        config=config,
        refine=refine,
        refine_span=refine_span,
        select_by=select_by,
    )
    if search_version != cohort.search_config_version:
        raise ValueError("production search policy does not match the frozen panel cohort")
    if config.version_hash != cohort.gate_config_version:
        raise ValueError("production gate policy does not match the frozen panel cohort")

    search_impl = run_search if run_search_fn is None else run_search_fn

    def search(frame: pd.DataFrame, symbol: str) -> Experiment:
        return search_impl(
            frame,
            symbol,
            strategies,
            config=config,
            prior_trials=0,
            n_per_param=n_per_param,
            refine=refine,
            refine_span=refine_span,
            select_by=select_by,
        )

    return search


def run_panel_null_replicate(
    cohort: PanelNullCohort,
    prepared: PreparedPanelNullSource,
    *,
    panel_index: int,
    search: Callable[[pd.DataFrame, str], Experiment],
) -> PanelNullReplicate:
    """Generate and search one indivisible whole-panel replicate."""
    cohort = PanelNullCohort.model_validate(cohort.model_dump())
    prepared = _revalidate_prepared_source(prepared)
    _require_prepared_cohort_identity(cohort, prepared)
    if not 0 <= panel_index < cohort.n_replicates:
        raise ValueError("panel_index is outside the frozen replicate range")

    seed = panel_seed(cohort.base_seed, panel_index)
    generated = joint_iid_panel_null(
        prepared.to_frames(),
        cohort.target_n_bars,
        seed=seed,
    )
    walk_forward_excesses: list[float] = []
    purged_cv_excesses: list[float] = []
    secondary_complete = True
    errors: list[PanelNullError] = []
    for symbol in cohort.symbols:
        try:
            experiment = Experiment.model_validate(
                search(generated[symbol].copy(deep=True), symbol)
            )
            if experiment.symbol != symbol:
                raise ValueError("search result symbol does not match the generated symbol")
            if experiment.n_bars != cohort.target_n_bars:
                raise ValueError("search result history does not match the panel cohort")
            if experiment.search_config_version != cohort.search_config_version:
                raise ValueError("search result search identity does not match the panel cohort")
            if experiment.gate_config.version_hash != cohort.gate_config_version:
                raise ValueError("search result gate identity does not match the panel cohort")

            finalist = selected_trial(experiment)
            if (
                finalist.walk_forward_oos_sharpe is None
                or experiment.walk_forward_hold_sharpe is None
            ):
                raise ValueError("search result is missing paired walk-forward diagnostics")
            walk_forward_excesses.append(
                finalist.walk_forward_oos_sharpe - experiment.walk_forward_hold_sharpe
            )
            if finalist.purged_cv_oos_sharpe is None or experiment.purged_cv_hold_sharpe is None:
                secondary_complete = False
            else:
                purged_cv_excesses.append(
                    finalist.purged_cv_oos_sharpe - experiment.purged_cv_hold_sharpe
                )
        except Exception as error:
            errors.append(PanelNullError(symbol=symbol, message=str(error) or type(error).__name__))

    if not walk_forward_excesses:
        raise ValueError("panel replicate produced no measured symbols")
    panel_identity = sha256(f"{cohort.model_dump_json()}:{panel_index}".encode()).hexdigest()
    return PanelNullReplicate(
        panel_index=panel_index,
        panel_id=panel_identity,
        seed=seed,
        successful_symbols=len(walk_forward_excesses),
        errors=tuple(errors),
        walk_forward_excess=float(np.median(walk_forward_excesses)),
        purged_cv_excess=(float(np.median(purged_cv_excesses)) if secondary_complete else None),
    )


def run_panel_null_batch(
    cohort: PanelNullCohort,
    source_path: Path,
    *,
    panel_indices: Sequence[int],
    output_path: Path,
    search: Callable[[pd.DataFrame, str], Experiment],
) -> PanelNullShard:
    """Run only the explicit complete panel indices and exclusively write one scratch shard."""
    prepared = load_prepared_panel_null_source(source_path)
    return _run_loaded_panel_null_batch(
        cohort,
        prepared,
        panel_indices=panel_indices,
        output_path=output_path,
        search=search,
    )


def _run_loaded_panel_null_batch(
    cohort: PanelNullCohort,
    prepared: PreparedPanelNullSource,
    *,
    panel_indices: Sequence[int],
    output_path: Path,
    search: Callable[[pd.DataFrame, str], Experiment],
) -> PanelNullShard:
    """Execute a batch after its prepared source has crossed the validated load boundary."""
    cohort = PanelNullCohort.model_validate(cohort.model_dump())
    prepared = _revalidate_prepared_source(prepared)
    indices = tuple(panel_indices)
    if not indices:
        raise ValueError("batch requires at least one explicit panel index")
    if len(set(indices)) != len(indices):
        raise ValueError("batch contains a duplicate panel index")
    if any(index < 0 or index >= cohort.n_replicates for index in indices):
        raise ValueError("panel index is outside the frozen replicate range")
    if Path(output_path).exists():
        raise FileExistsError(output_path)

    replicates = tuple(
        run_panel_null_replicate(
            cohort,
            prepared,
            panel_index=panel_index,
            search=search,
        )
        for panel_index in sorted(indices)
    )
    shard = PanelNullShard(cohort=cohort, replicates=replicates)
    save_panel_null_shard(shard, output_path)
    return shard


def run_production_panel_null_batch(
    cohort_path: Path,
    source_path: Path,
    *,
    strategy_names: Sequence[str],
    config: GateConfig,
    panel_indices: Sequence[int],
    output_path: Path,
    n_per_param: int = 3,
    refine: bool = True,
    refine_span: float = 0.25,
    select_by: Literal["observed", "walk_forward"] = "observed",
    run_search_fn: Callable[..., Experiment] | None = None,
) -> PanelNullShard:
    """Load one frozen job identity before constructing and running its production batch."""
    cohort = load_panel_null_cohort(cohort_path)
    prepared = load_prepared_panel_null_source(source_path)
    _require_prepared_cohort_identity(cohort, prepared)
    search = make_production_panel_null_search(
        cohort,
        strategy_names,
        config=config,
        n_per_param=n_per_param,
        refine=refine,
        refine_span=refine_span,
        select_by=select_by,
        run_search_fn=run_search_fn,
    )
    return _run_loaded_panel_null_batch(
        cohort,
        prepared,
        panel_indices=panel_indices,
        output_path=output_path,
        search=search,
    )


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


def _exact_tail_interval(count: int, n_replicates: int) -> BinomialConfidenceInterval:
    bound_alpha = (1.0 - _TAIL_INTERVAL_CONFIDENCE) / 2.0
    low = 0.0 if count == 0 else float(beta.ppf(bound_alpha, count, n_replicates - count + 1))
    high = (
        1.0
        if count == n_replicates
        else float(beta.ppf(1.0 - bound_alpha, count + 1, n_replicates - count))
    )
    return BinomialConfidenceInterval(low=low, high=high)


def _infer_diagnostic(
    diagnostic: Literal["walk_forward", "purged_cv"],
    real_values: Sequence[float],
    null_values: Sequence[float],
) -> PanelDiagnosticInference:
    real_statistic = float(np.median(real_values))
    null_array = np.asarray(null_values, dtype=float)
    n_replicates = len(null_values)
    lower_count = int(np.count_nonzero(null_array <= real_statistic))
    upper_count = int(np.count_nonzero(null_array >= real_statistic))
    lower_interval = _exact_tail_interval(lower_count, n_replicates)
    upper_interval = _exact_tail_interval(upper_count, n_replicates)

    resolution: Literal["separated_below", "separated_above", "not_separated", "unresolved"]
    if lower_interval.high < _TAIL_THRESHOLD:
        resolution = "separated_below"
    elif upper_interval.high < _TAIL_THRESHOLD:
        resolution = "separated_above"
    elif lower_interval.low > _TAIL_THRESHOLD and upper_interval.low > _TAIL_THRESHOLD:
        resolution = "not_separated"
    else:
        resolution = "unresolved"

    plus_one_lower = (1 + lower_count) / (n_replicates + 1)
    plus_one_upper = (1 + upper_count) / (n_replicates + 1)
    return PanelDiagnosticInference(
        diagnostic=diagnostic,
        real_statistic=real_statistic,
        null_median=float(np.median(null_array)),
        null_p025=float(np.percentile(null_array, 2.5)),
        null_p975=float(np.percentile(null_array, 97.5)),
        n_replicates=n_replicates,
        lower_tail_count=lower_count,
        upper_tail_count=upper_count,
        two_sided_p_value=min(1.0, 2.0 * min(plus_one_lower, plus_one_upper)),
        lower_tail_interval=lower_interval,
        upper_tail_interval=upper_interval,
        resolution=resolution,
    )


def infer_panel_null(calibration: PanelNullCalibration) -> PanelNullInference:
    """Apply the fixed ADR-081/082 interpretation to a complete panel measurement."""
    walk_forward = _infer_diagnostic(
        "walk_forward",
        [value.walk_forward for value in calibration.cohort.symbol_excesses],
        [replicate.walk_forward_excess for replicate in calibration.replicates],
    )

    real_purged = [value.purged_cv for value in calibration.cohort.symbol_excesses]
    null_purged = [replicate.purged_cv_excess for replicate in calibration.replicates]
    purged_cv = None
    if all(value is not None for value in real_purged) and all(
        value is not None for value in null_purged
    ):
        purged_cv = _infer_diagnostic(
            "purged_cv",
            [value for value in real_purged if value is not None],
            [value for value in null_purged if value is not None],
        )

    return PanelNullInference(walk_forward=walk_forward, purged_cv=purged_cv)


def _validate_shard_replicates(
    cohort: PanelNullCohort,
    replicates: Sequence[PanelNullReplicate],
) -> None:
    if not replicates:
        raise ValueError("shard must contain at least one complete panel replicate")
    if any(
        not isfinite(value.walk_forward)
        or (value.purged_cv is not None and not isfinite(value.purged_cv))
        for value in cohort.symbol_excesses
    ):
        raise ValueError("symbol excess statistics must be finite")
    indices = [replicate.panel_index for replicate in replicates]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate panel index")
    if any(index < 0 or index >= cohort.n_replicates for index in indices):
        raise ValueError("panel index is outside the frozen replicate range")
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


def _validate_complete_replicates(
    cohort: PanelNullCohort,
    replicates: Sequence[PanelNullReplicate],
) -> None:
    _validate_shard_replicates(cohort, replicates)
    indices = [replicate.panel_index for replicate in replicates]
    if set(indices) != set(range(cohort.n_replicates)):
        raise ValueError("shards must contain the complete panel indices")


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
