"""ExperimentManifest: JSON round-trips with all lineage fields preserved; parameter hash is order-independent and distinct for different params."""

from datetime import date
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.research.backtesting.manifest import ExperimentManifest, compute_parameter_hash


def _manifest(**overrides: object) -> ExperimentManifest:
    base: dict[str, object] = {
        "git_commit_hash": "a" * 40,
        "strategy_name": "sma_crossover",
        "parameter_hash": compute_parameter_hash({"fast": 5, "slow": 10}),
        "data_source": "yfinance",
        "symbol": "AAPL",
        "start_date": date(2020, 1, 1),
        "end_date": date(2024, 1, 1),
        "adapter_version": "yfinance-1.4.0",
    }
    base.update(overrides)
    return ExperimentManifest(**base)  # type: ignore[arg-type]


def test_manifest_round_trips_json_with_all_fields() -> None:
    # §8 invariant #10: round-trips JSON with all fields preserved.
    manifest = _manifest(data_quality_report_id=uuid4(), validation_config_hash="c" * 64)
    restored = ExperimentManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_manifest_defaults_are_populated() -> None:
    manifest = _manifest()
    assert manifest.experiment_id is not None
    assert manifest.benchmark_symbol == "SPY"
    assert manifest.created_at.tzinfo is not None
    assert manifest.data_quality_report_id is None


def test_parameter_hash_is_order_independent() -> None:
    assert compute_parameter_hash({"fast": 5, "slow": 10}) == compute_parameter_hash(
        {"slow": 10, "fast": 5}
    )


def test_parameter_hash_differs_for_different_params() -> None:
    assert compute_parameter_hash({"fast": 5}) != compute_parameter_hash({"fast": 6})


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"created_at": "2026-10-04T10:00:00"}, "timezone-aware"),
        ({"git_commit_hash": "abc123"}, "git_commit_hash"),
        ({"strategy_name": ""}, "strategy_name"),
        ({"parameter_hash": "bad"}, "manifest hashes"),
        ({"data_source": " "}, "data_source"),
        ({"symbol": ""}, "symbol"),
        ({"start_date": date(2024, 1, 1), "end_date": date(2024, 1, 1)}, "before"),
        ({"adapter_version": ""}, "adapter_version"),
        ({"validation_config_hash": "bad"}, "manifest hashes"),
        ({"benchmark_symbol": ""}, "benchmark_symbol"),
    ],
)
def test_manifest_rejects_invalid_lineage_identity(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _manifest(**updates)


def test_manifest_normalizes_symbol_identity() -> None:
    manifest = _manifest(symbol=" aapl ", benchmark_symbol=" spy ")
    assert manifest.symbol == "AAPL"
    assert manifest.benchmark_symbol == "SPY"
