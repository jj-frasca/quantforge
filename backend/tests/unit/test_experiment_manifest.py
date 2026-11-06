"""ExperimentManifest: JSON round-trips with all lineage fields preserved; parameter hash is order-independent and distinct for different params."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
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


_hex40 = st.text(alphabet="0123456789abcdef", min_size=40, max_size=40)
_hex64 = st.text(alphabet="0123456789abcdef", min_size=64, max_size=64)
_identity_text = st.text(min_size=1, max_size=24).filter(lambda s: s.strip() != "")


@given(
    experiment_id=st.uuids(),
    created_at=st.datetimes(timezones=st.just(UTC)),
    git_commit_hash=_hex40,
    strategy_name=_identity_text,
    parameter_hash=_hex64,
    data_source=_identity_text,
    symbol=_identity_text,
    start_date=st.dates(),
    end_date=st.dates(),
    data_quality_report_id=st.one_of(st.none(), st.uuids()),
    adapter_version=_identity_text,
    validation_config_hash=st.one_of(st.none(), _hex64),
    benchmark_symbol=_identity_text,
)
def test_manifest_round_trips_json_for_arbitrary_field_values(
    experiment_id: UUID,
    created_at: datetime,
    git_commit_hash: str,
    strategy_name: str,
    parameter_hash: str,
    data_source: str,
    symbol: str,
    start_date: date,
    end_date: date,
    data_quality_report_id: UUID | None,
    adapter_version: str,
    validation_config_hash: str | None,
    benchmark_symbol: str,
) -> None:
    # §8 invariant #10: round-trips JSON with all fields preserved, for arbitrary valid field
    # values -- not just the one fixed example above. Each generator respects the model's own
    # validators (git_commit_hash: 40-hex, parameter_hash/validation_config_hash: 64-hex,
    # start_date < end_date) rather than arbitrary text, since an invalid draw would raise before
    # the round-trip is ever exercised.
    assume(start_date != end_date)
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    manifest = ExperimentManifest(
        experiment_id=experiment_id,
        created_at=created_at,
        git_commit_hash=git_commit_hash,
        strategy_name=strategy_name,
        parameter_hash=parameter_hash,
        data_source=data_source,
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
        data_quality_report_id=data_quality_report_id,
        adapter_version=adapter_version,
        validation_config_hash=validation_config_hash,
        benchmark_symbol=benchmark_symbol,
    )
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
