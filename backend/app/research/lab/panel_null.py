"""Replicated whole-panel null artifact contracts (ADR-081).

This module deliberately contains identity and consolidation only. Generation, inference, and the
manual sole-writer workflow build on these contracts without being able to reinterpret a partial
symbol shard as an independent panel observation.
"""

from collections.abc import Sequence
from datetime import date
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PanelSymbolExcess(BaseModel):
    """The frozen real-side value for one equally weighted cohort symbol."""

    model_config = ConfigDict(frozen=True)

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

    model_config = ConfigDict(frozen=True)

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


def panel_seed(base_seed: int, panel_index: int) -> int:
    """Derive a batching-invariant signed-64-bit seed from one global panel index."""
    if base_seed < 0:
        raise ValueError("base_seed must be non-negative")
    if panel_index < 0:
        raise ValueError("panel_index must be non-negative")
    digest = sha256(f"{base_seed}:{panel_index}".encode()).digest()
    return int.from_bytes(digest[:8], "big") & ((1 << 63) - 1)


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
    indices = [replicate.panel_index for replicate in replicates]
    if len(set(indices)) != len(indices):
        raise ValueError("duplicate panel index")
    expected_indices = set(range(cohort.n_replicates))
    if set(indices) != expected_indices:
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
        error_symbols = [error.symbol for error in replicate.errors]
        if len(set(error_symbols)) != len(error_symbols):
            raise ValueError("replicate contains a duplicate error symbol")
        if any(symbol not in cohort_symbols for symbol in error_symbols):
            raise ValueError("replicate contains an error symbol outside the frozen cohort")
    if any(
        replicate.successful_symbols < cohort.min_successful_symbols for replicate in replicates
    ):
        raise ValueError("replicate is below the successful-symbol floor")
    for replicate in replicates:
        if replicate.successful_symbols + len(replicate.errors) != len(cohort.symbols):
            raise ValueError("replicate must account for every cohort symbol")

    ordered = tuple(sorted(replicates, key=lambda replicate: replicate.panel_index))
    return PanelNullCalibration(cohort=cohort, replicates=ordered)
