"""ADR-137: real-data research inputs are quality-gated and lineage-bearing."""

from datetime import UTC, datetime, timedelta

import pytest
from tests.fixtures.synthetic import builders

from app.data.models import DataQualityIssue, DataQualityReport
from app.research.dataset import ResearchDatasetEvidence, prepare_research_dataset


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
    assert (
        ResearchDatasetEvidence.model_validate_json(dataset.evidence().model_dump_json())
        == dataset.evidence()
    )


def _evidence_payload() -> dict[str, object]:
    return {
        "quality_report": DataQualityReport(
            symbol="AAPL", source="yfinance", checked_at=datetime(2024, 1, 2, tzinfo=UTC)
        ),
        "source": "yfinance",
        "adapter_version": "test-1",
        "start": datetime(2024, 1, 1, tzinfo=UTC),
        "end": datetime(2024, 1, 2, tzinfo=UTC),
        "git_commit_hash": "a" * 40,
    }


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        (
            {
                "quality_report": DataQualityReport(
                    symbol="AAPL",
                    source="yfinance",
                    checked_at=datetime(2024, 1, 2, tzinfo=UTC),
                    issues=[
                        DataQualityIssue(
                            check="source_mismatch", severity="error", message="flags mismatch"
                        )
                    ],
                )
            },
            "passed quality report",
        ),
        ({"source": "alpaca"}, "source does not match"),
        ({"adapter_version": " "}, "adapter_version"),
        ({"end": datetime(2024, 1, 1, tzinfo=UTC)}, "start must be before end"),
        ({"git_commit_hash": "not-a-sha"}, "git_commit_hash"),
    ],
)
def test_dataset_evidence_rejects_identity_drift(updates: dict[str, object], message: str) -> None:
    payload = _evidence_payload()
    payload.update(updates)

    with pytest.raises(ValueError, match=message):
        ResearchDatasetEvidence.model_validate(payload)


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
