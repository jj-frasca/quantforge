"""ExperimentManifest: JSON round-trips with all lineage fields preserved; parameter hash is order-independent and distinct for different params."""

from datetime import date
from uuid import uuid4

from app.research.backtesting.manifest import ExperimentManifest, compute_parameter_hash


def _manifest(**overrides: object) -> ExperimentManifest:
    base: dict[str, object] = {
        "git_commit_hash": "abc123",
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
    manifest = _manifest(data_quality_report_id=uuid4(), validation_config_hash="cfg1")
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
