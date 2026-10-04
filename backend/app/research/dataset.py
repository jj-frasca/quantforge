"""Quality-gated real-data input for durable research claims (ADR-137)."""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from os import environ
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd
from pandas.api.types import is_bool_dtype, is_complex_dtype, is_numeric_dtype
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.data.models import DataQualityReport, PriceBar, Source
from app.data.quality.engine import DataQualityEngine
from app.data.sources.base import DataSourceAdapter
from app.research.frames import bars_to_frame

_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")


def _copy_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Isolate canonical numeric data and axes, including pandas' shared index storage."""
    copied = frame.copy(deep=True)
    copied.index = frame.index.copy(deep=True)
    copied.columns = frame.columns.copy(deep=True)
    return copied


class _DatasetFrame:
    """Required dataclass field with private capture and writable copy-on-read (ADR-165)."""

    def __get__(
        self, instance: "ResearchDataset | None", owner: "type[ResearchDataset] | None" = None
    ) -> pd.DataFrame:
        if instance is None:
            # No class-level frame exists; callers must supply an instance.
            raise AttributeError("frame requires an explicit value")
        return _copy_frame(instance._frame)

    def __set__(self, instance: "ResearchDataset", value: pd.DataFrame) -> None:
        object.__setattr__(instance, "_frame", _copy_frame(value))


class ResearchDatasetEvidence(BaseModel):
    """Serializable identity of one exact quality-checked vendor dataset (ADR-139)."""

    model_config = ConfigDict(frozen=True, revalidate_instances="always")

    quality_report: DataQualityReport
    source: Source
    adapter_version: str
    start: datetime
    end: datetime
    git_commit_hash: str

    @field_validator("start", "end")
    @classmethod
    def _coerce_interval_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dataset evidence interval must be timezone-aware")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_identity(self) -> "ResearchDatasetEvidence":
        if not self.quality_report.passed:
            raise ValueError("dataset evidence requires a passed quality report")
        if self.quality_report.source != self.source:
            raise ValueError("quality report source does not match dataset evidence source")
        if not self.adapter_version.strip():
            raise ValueError("adapter_version must be non-empty")
        if self.start >= self.end:
            raise ValueError("dataset evidence start must be before end")
        if not _FULL_GIT_SHA.fullmatch(self.git_commit_hash):
            raise ValueError("git_commit_hash must be a 40-character lowercase hexadecimal SHA")
        return self


@dataclass(frozen=True)
class ResearchDataset:
    """One exact, quality-checked vendor dataset and its reproducibility identity."""

    frame: pd.DataFrame
    quality_report: DataQualityReport
    source: Source
    adapter_version: str
    start: datetime
    end: datetime
    git_commit_hash: str
    _frame: pd.DataFrame = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        identity = self.evidence()
        object.__setattr__(self, "quality_report", identity.quality_report)
        object.__setattr__(self, "start", identity.start)
        object.__setattr__(self, "end", identity.end)
        frame = self._frame
        if frame.empty:
            raise ValueError("research dataset frame must be non-empty")
        if not isinstance(frame.index, pd.DatetimeIndex):
            raise ValueError("research dataset frame requires a DatetimeIndex")
        if frame.index.tz is None:
            raise ValueError("research dataset frame index must be timezone-aware")
        if not frame.index.is_monotonic_increasing or not frame.index.is_unique:
            raise ValueError("research dataset frame index must be unique and ascending")
        if frame.index[0] < self.start or frame.index[-1] >= self.end:
            raise ValueError("research dataset frame timestamps must lie within [start, end)")
        if (
            isinstance(frame.columns, pd.MultiIndex)
            or not frame.columns.is_unique
            or "close" not in frame.columns
        ):
            raise ValueError("research dataset frame requires unique flat columns including close")
        if any(
            not is_numeric_dtype(dtype) or is_bool_dtype(dtype) or is_complex_dtype(dtype)
            for dtype in frame.dtypes
        ):
            raise ValueError("research dataset frame columns must contain real numeric values")
        if not np.isfinite(frame.to_numpy(dtype=float, na_value=np.nan)).all():
            raise ValueError("research dataset frame values must be finite")
        price_columns = [name for name in ("open", "high", "low", "close") if name in frame]
        if (frame[price_columns] <= 0.0).any().any():
            raise ValueError("research dataset frame prices must be positive")
        if "high" in frame and any(
            (frame["high"] < frame[name]).any() for name in price_columns if name != "high"
        ):
            raise ValueError("research dataset frame high must bound all present prices")
        if "low" in frame and any(
            (frame["low"] > frame[name]).any() for name in price_columns if name != "low"
        ):
            raise ValueError("research dataset frame low must bound all present prices")
        if "volume" in frame and (frame["volume"] < 0.0).any():
            raise ValueError("research dataset frame volume must be non-negative")

    def evidence(self) -> ResearchDatasetEvidence:
        """Freeze the serializable acquisition identity beside a durable derived result."""
        return ResearchDatasetEvidence(
            quality_report=self.quality_report,
            source=self.source,
            adapter_version=self.adapter_version,
            start=self.start,
            end=self.end,
            git_commit_hash=self.git_commit_hash,
        )


# Install after decoration so both dataclasses and static typing retain a required init field.
# The generated frozen initializer still calls the descriptor through object.__setattr__.
ResearchDataset.frame = cast(pd.DataFrame, _DatasetFrame())


def prepare_research_dataset(
    bars: list[PriceBar],
    *,
    symbol: str,
    source: Source,
    adapter_version: str,
    start: datetime,
    end: datetime,
    git_commit_hash: str,
) -> ResearchDataset:
    """Run ADR-006 before exposing vendor bars to StrategyLab."""
    report = DataQualityEngine().check(
        bars,
        symbol,
        expected_source=source,
        expected_start=start,
        expected_end=end,
    )
    if not report.passed:
        checks = ", ".join(issue.check for issue in report.issues if issue.severity == "error")
        raise ValueError(f"quality report failed for {report.symbol}: {checks}")
    return ResearchDataset(
        frame=bars_to_frame(bars),
        quality_report=report,
        source=source,
        adapter_version=adapter_version,
        start=start,
        end=end,
        git_commit_hash=git_commit_hash,
    )


def current_git_revision() -> str:
    """Return the exact code revision executed locally or by GitHub Actions."""
    revision = environ.get("GITHUB_SHA")
    if revision is None:
        repository_root = Path(__file__).resolve().parents[3]
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repository_root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    if not _FULL_GIT_SHA.fullmatch(revision):
        raise ValueError("git revision must be a 40-character lowercase hexadecimal SHA")
    return revision


def fetch_research_dataset(
    adapter: DataSourceAdapter,
    symbol: str,
    start: datetime,
    end: datetime,
    *,
    git_commit_hash: str,
) -> ResearchDataset:
    """Fetch canonical bars once, quality-check them, and retain their exact lineage."""
    return prepare_research_dataset(
        adapter.fetch_price_bars(symbol, start, end),
        symbol=symbol,
        source=adapter.source,
        adapter_version=adapter.adapter_version,
        start=start,
        end=end,
        git_commit_hash=git_commit_hash,
    )
