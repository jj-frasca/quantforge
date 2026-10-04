"""ADR-137: real-data research inputs are quality-gated and lineage-bearing."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest
from tests.fixtures.synthetic import builders

from app.data.models import DataQualityIssue, DataQualityReport
from app.research.cross_sectional.forward import CrossSectionalForwardScore
from app.research.dataset import ResearchDatasetEvidence, prepare_research_dataset
from app.research.lab.paper import ForwardScore


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


@pytest.mark.parametrize("naive_fields", [("start",), ("end",), ("start", "end")])
def test_dataset_evidence_naive_interval_rejected(naive_fields: tuple[str, ...]) -> None:
    payload = _evidence_payload()
    for name in naive_fields:
        value = payload[name]
        assert isinstance(value, datetime)
        payload[name] = value.replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        ResearchDatasetEvidence.model_validate(payload)


def test_dataset_evidence_offset_interval_normalizes_to_utc() -> None:
    payload = _evidence_payload()
    for name in ("start", "end"):
        value = payload[name]
        assert isinstance(value, datetime)
        payload[name] = value.astimezone(timezone(timedelta(hours=-7)))
    evidence = ResearchDatasetEvidence.model_validate(payload)
    assert evidence.start == datetime(2024, 1, 1, tzinfo=UTC)
    assert evidence.end == datetime(2024, 1, 2, tzinfo=UTC)
    assert evidence.start.tzinfo is UTC
    assert evidence.end.tzinfo is UTC
    assert ResearchDatasetEvidence.model_validate_json(evidence.model_dump_json()) == evidence


@pytest.mark.parametrize(
    "updates",
    [
        {"source": "bogus"},
        {"adapter_version": " "},
        {"git_commit_hash": "invalid"},
        {"start": datetime(2024, 1, 1)},
        {
            "quality_report": DataQualityReport(
                symbol="AAPL", source="yfinance", checked_at=datetime(2024, 1, 2, tzinfo=UTC)
            ).model_copy(update={"checked_at": datetime(2024, 1, 2)})
        },
    ],
)
@pytest.mark.parametrize("consumer", ["evidence", "single_name", "panel"])
def test_dataset_evidence_unchecked_copy_rejected_by_consumers(
    updates: dict[str, object], consumer: str
) -> None:
    evidence = ResearchDatasetEvidence.model_validate(_evidence_payload()).model_copy(
        update=updates
    )
    score = {
        "forward_bars": 0,
        "forward_return": 0.0,
        "forward_sharpe": 0.0,
        "as_of": datetime(2024, 1, 2, tzinfo=UTC),
    }
    with pytest.raises(ValueError):
        if consumer == "evidence":
            ResearchDatasetEvidence.model_validate(evidence)
        elif consumer == "single_name":
            ForwardScore.model_validate(
                dict(
                    score,
                    buy_and_hold_return=0.0,
                    buy_and_hold_sharpe=0.0,
                    beats_buy_and_hold=False,
                    evidence=evidence,
                )
            )
        else:
            CrossSectionalForwardScore.model_validate(
                dict(
                    score,
                    benchmark_return=0.0,
                    benchmark_sharpe=0.0,
                    beats_benchmark=False,
                    evidence=[evidence],
                )
            )


@pytest.mark.parametrize("field", ["start", "end", "quality_report"])
def test_research_dataset_direct_replacement_revalidates_identity(field: str) -> None:
    bars = builders.clean_series(symbol="AAPL", n=120)
    dataset = prepare_research_dataset(
        bars,
        symbol="AAPL",
        source="yfinance",
        adapter_version="test-1",
        start=bars[0].timestamp_utc - timedelta(days=1),
        end=bars[-1].timestamp_utc + timedelta(days=1),
        git_commit_hash="a" * 40,
    )
    if field == "quality_report":
        value = dataset.quality_report.model_copy(update={"checked_at": datetime(2024, 1, 2)})
    else:
        value = getattr(dataset, field).replace(tzinfo=None)
    with pytest.raises(ValueError, match="timezone-aware"):
        replace(dataset, **{field: value})


def test_research_dataset_direct_replacement_preserves_validated_snapshot() -> None:
    bars = builders.clean_series(symbol="AAPL", n=120)
    dataset = prepare_research_dataset(
        bars,
        symbol="AAPL",
        source="yfinance",
        adapter_version="test-1",
        start=bars[0].timestamp_utc - timedelta(days=1),
        end=bars[-1].timestamp_utc + timedelta(days=1),
        git_commit_hash="a" * 40,
    )
    offset = timezone(timedelta(hours=5, minutes=30))
    copied = replace(
        dataset, start=dataset.start.astimezone(offset), end=dataset.end.astimezone(offset)
    )
    assert copied.start.tzinfo is UTC
    assert copied.end.tzinfo is UTC
    assert copied.quality_report == dataset.quality_report
    assert copied.quality_report is not dataset.quality_report
    assert copied.evidence() == dataset.evidence()


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
