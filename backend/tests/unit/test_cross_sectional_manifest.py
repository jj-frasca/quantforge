"""Standalone panel-lineage identity contracts (ADR-163)."""

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.research.cross_sectional.manifest import (
    CrossSectionalManifest,
    PanelComponentManifest,
)


def _component(**updates: object) -> PanelComponentManifest:
    payload: dict[str, object] = {
        "symbol": "AAPL",
        "data_source": "yfinance",
        "adapter_version": "adapter-v1",
        "start_date": date(2020, 1, 1),
        "end_date": date(2024, 1, 1),
        "data_quality_report_id": uuid4(),
    }
    payload.update(updates)
    return PanelComponentManifest.model_validate(payload)


def _manifest(**updates: object) -> CrossSectionalManifest:
    payload: dict[str, object] = {
        "experiment_id": uuid4(),
        "created_at": datetime(2026, 10, 4, tzinfo=UTC),
        "git_commit_hash": "a" * 40,
        "strategy_name": "xs_momentum",
        "parameter_hash": "b" * 64,
        "validation_config_hash": "c" * 64,
        "components": [_component()],
        "benchmark": "equal_weight_universe",
    }
    payload.update(updates)
    return CrossSectionalManifest.model_validate(payload)


def test_panel_manifest_components_are_defensive_immutable_and_round_trip() -> None:
    component = _component()
    components = [component]
    manifest = _manifest(components=components)
    before = manifest.model_dump(mode="json")

    components.clear()
    assert manifest.model_dump(mode="json") == before
    with pytest.raises(AttributeError, match="immutable"):
        manifest.components.clear()

    restored = CrossSectionalManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest
    assert restored.model_dump(mode="json") == before


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({"strategy_name": ""}, "strategy_name"),
        ({"benchmark": " "}, "benchmark"),
        ({"components": [_component().model_copy(update={"adapter_version": ""})]}, "adapter"),
    ],
)
def test_panel_manifest_rejects_invalid_or_unchecked_identity(
    updates: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        _manifest(**updates)
