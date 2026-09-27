"""Quality-gated real-data input for durable research claims (ADR-137)."""

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from os import environ
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, model_validator

from app.data.models import DataQualityReport, PriceBar, Source
from app.data.quality.engine import DataQualityEngine
from app.data.sources.base import DataSourceAdapter
from app.research.frames import bars_to_frame

_FULL_GIT_SHA = re.compile(r"[0-9a-f]{40}")


class ResearchDatasetEvidence(BaseModel):
    """Serializable identity of one exact quality-checked vendor dataset (ADR-139)."""

    model_config = ConfigDict(frozen=True)

    quality_report: DataQualityReport
    source: Source
    adapter_version: str
    start: datetime
    end: datetime
    git_commit_hash: str

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

    def __post_init__(self) -> None:
        if not self.quality_report.passed:
            raise ValueError("research dataset requires a passed quality report")
        if self.quality_report.source != self.source:
            raise ValueError("quality report source does not match research dataset source")
        if not self.adapter_version.strip():
            raise ValueError("adapter_version must be non-empty")
        if not _FULL_GIT_SHA.fullmatch(self.git_commit_hash):
            raise ValueError("git_commit_hash must be a 40-character lowercase hexadecimal SHA")
        if self.start >= self.end:
            raise ValueError("research dataset start must be before end")
        if self.frame.empty:
            raise ValueError("research dataset frame must be non-empty")
        if not isinstance(self.frame.index, pd.DatetimeIndex):
            raise ValueError("research dataset frame requires a DatetimeIndex")
        if self.frame.index.tz is None:
            raise ValueError("research dataset frame index must be timezone-aware")
        if not self.frame.index.is_monotonic_increasing or not self.frame.index.is_unique:
            raise ValueError("research dataset frame index must be unique and ascending")

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
