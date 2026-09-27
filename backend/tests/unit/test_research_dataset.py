"""ADR-137: real-data research inputs are quality-gated and lineage-bearing."""

from datetime import timedelta

import pytest
from tests.fixtures.synthetic import builders

from app.research.dataset import prepare_research_dataset


def test_prepare_research_dataset_carries_passed_quality_identity() -> None:
    bars = builders.clean_series(symbol="aapl", n=120)

    dataset = prepare_research_dataset(
        bars,
        symbol=" aapl ",
        source="yfinance",
        adapter_version="yfinance-test",
        start=bars[0].timestamp_utc - timedelta(days=1),
        end=bars[-1].timestamp_utc + timedelta(days=1),
        git_commit_hash="a" * 40,
    )

    assert dataset.quality_report.passed is True
    assert dataset.quality_report.symbol == "AAPL"
    assert dataset.quality_report.source == "yfinance"
    assert dataset.frame.index.is_unique
    assert dataset.git_commit_hash == "a" * 40


def test_prepare_research_dataset_rejects_failed_quality_evidence() -> None:
    bars = builders.clean_series(symbol="AAPL", n=120)
    duplicate = bars[0].model_copy(
        update={"timestamp_utc": bars[1].timestamp_utc, "source": "yfinance"}
    )

    with pytest.raises(ValueError, match=r"quality report failed.*duplicate_timestamp"):
        prepare_research_dataset(
            [*bars, duplicate],
            symbol="AAPL",
            source="yfinance",
            adapter_version="yfinance-test",
            start=bars[0].timestamp_utc - timedelta(days=1),
            end=bars[-1].timestamp_utc + timedelta(days=1),
            git_commit_hash="b" * 40,
        )


@pytest.mark.parametrize("revision", ["", "abc123", "G" * 40])
def test_prepare_research_dataset_rejects_noncanonical_code_revision(revision: str) -> None:
    bars = builders.clean_series(symbol="AAPL", n=120)

    with pytest.raises(ValueError, match="git_commit_hash"):
        prepare_research_dataset(
            bars,
            symbol="AAPL",
            source="yfinance",
            adapter_version="yfinance-test",
            start=bars[0].timestamp_utc - timedelta(days=1),
            end=bars[-1].timestamp_utc + timedelta(days=1),
            git_commit_hash=revision,
        )
