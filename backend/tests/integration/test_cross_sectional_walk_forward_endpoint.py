"""ADR-322: the read-only endpoint publishes exact, attributed stored WF evidence."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.cross_sectional import CrossSectionalView, _view, get_pool_path
from app.main import app
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.lab.gate import GateConfig

METHOD = "family-walk-forward-equal-weight-continuation-v1"


@pytest.fixture
def endpoint(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    pool = tmp_path / "pool.json"
    app.dependency_overrides[get_pool_path] = lambda: pool
    client = TestClient(app)
    try:
        yield client, pool
    finally:
        client.close()
        app.dependency_overrides.pop(get_pool_path, None)


def _experiment(*, day: int = 2, measured: bool = True) -> CrossSectionalExperiment:
    trials = [
        CrossSectionalTrial(
            strategy_name=name,
            parameters={"lookback": 5, "quantile": 0.2},
            observed_sharpe=0.2,
            deflated_sharpe=-0.3,
            pbo=0.6,
            parameter_stability_score=0.7,
            walk_forward_oos_sharpe=score,
        )
        for name, score in (("xs_momentum", 0.0), ("xs_reversal", -0.375))
    ]
    return CrossSectionalExperiment(
        created_at=datetime(2026, 10, day, tzinfo=UTC),
        universe_symbols=["A", "B"],
        strategy_names=[trial.strategy_name for trial in trials],
        gate_config=GateConfig(),
        trials=trials,
        lifetime_trials=2,
        walk_forward_method=METHOD if measured else None,
        walk_forward_hold_sharpe=-0.125 if measured else None,
        walk_forward_n_bars=348 if measured else None,
        walk_forward_n_splits=3 if measured else None,
    )


def _view_payload() -> dict[str, Any]:
    return {
        "created_at": datetime(2026, 10, 2, tzinfo=UTC),
        "universe_size": 2,
        "best_strategy_name": None,
        "graduated": False,
        "graduate_holdout_sharpe": None,
        "trials": [
            {
                "strategy_name": "xs_momentum",
                "observed_sharpe": 0.2,
                "deflated_sharpe": -0.3,
                "pbo": 0.6,
                "parameter_stability_score": 0.7,
                "walk_forward_oos_sharpe": 0.0,
            }
        ],
        "walk_forward_method": METHOD,
        "walk_forward_hold_sharpe": -0.125,
        "walk_forward_n_bars": 348,
        "walk_forward_n_splits": 3,
    }


def test_latest_measured_families_publish_exact_zero_negative_pair_and_geometry(
    endpoint: tuple[TestClient, Path],
) -> None:
    client, pool = endpoint
    store = JsonFileCrossSectionalStore(pool)
    store.add(_experiment(day=1, measured=False))
    latest = _experiment()
    store.add(latest)
    original_bytes = pool.read_bytes()
    response = client.get("/api/v1/cross-sectional")
    assert response.status_code == 200
    body = response.json()
    assert body["walk_forward_method"] == METHOD
    assert body["walk_forward_hold_sharpe"] == latest.walk_forward_hold_sharpe == -0.125
    assert body["walk_forward_n_bars"] == 348
    assert body["walk_forward_n_splits"] == 3
    assert [trial["walk_forward_oos_sharpe"] for trial in body["trials"]] == [0.0, -0.375]
    assert [trial["strategy_name"] for trial in body["trials"]] == latest.strategy_names
    assert pool.read_bytes() == original_bytes


@pytest.mark.parametrize("scalar", [None, -0.75])
def test_newer_legacy_record_retains_omitted_null_or_unpaired_evidence(
    endpoint: tuple[TestClient, Path],
    scalar: float | None,
) -> None:
    client, pool = endpoint
    measured = _experiment(day=1).model_dump(mode="json")
    legacy = _experiment(day=2, measured=False).model_dump(mode="json")
    for name in (
        "walk_forward_method",
        "walk_forward_hold_sharpe",
        "walk_forward_n_bars",
        "walk_forward_n_splits",
    ):
        legacy.pop(name)
    legacy["trials"][0]["walk_forward_oos_sharpe"] = scalar
    legacy["trials"][1].pop("walk_forward_oos_sharpe")
    pool.write_text(json.dumps([measured, legacy]) + "\n")
    body = client.get("/api/v1/cross-sectional").json()
    assert body["walk_forward_method"] is None
    assert body["walk_forward_hold_sharpe"] is None
    assert body["walk_forward_n_bars"] is None and body["walk_forward_n_splits"] is None
    assert [trial["walk_forward_oos_sharpe"] for trial in body["trials"]] == [scalar, None]


@pytest.mark.parametrize("present", [False, True])
def test_missing_or_empty_pool_still_returns_null(
    endpoint: tuple[TestClient, Path],
    present: bool,
) -> None:
    client, pool = endpoint
    if present:
        pool.write_text("[]\n")
    response = client.get("/api/v1/cross-sectional")
    assert response.status_code == 200 and response.json() is None


@pytest.mark.parametrize(
    "change",
    [
        {"walk_forward_method": "future-unknown-method"},
        {"walk_forward_hold_sharpe": float("nan")},
        {"walk_forward_hold_sharpe": float("inf")},
        {"walk_forward_hold_sharpe": None},
        {"walk_forward_n_bars": None},
        {"walk_forward_n_splits": None},
        {"walk_forward_n_bars": 3},
        {"walk_forward_n_splits": 0},
        {"walk_forward_n_splits": True},
        {"walk_forward_n_bars": 348.0},
        {"walk_forward_n_splits": "3"},
        {"trials": []},
    ],
)
def test_direct_measured_view_rejects_invalid_or_incomplete_metadata(
    change: dict[str, Any],
) -> None:
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate({**_view_payload(), **change})


@pytest.mark.parametrize("score", [None, float("nan"), float("inf")])
def test_measured_view_requires_every_family_finite_mean(score: float | None) -> None:
    payload = _view_payload()
    payload["trials"][0]["walk_forward_oos_sharpe"] = score
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(payload)


@pytest.mark.parametrize(
    "field", ["walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"]
)
def test_direct_legacy_view_cannot_publish_unattributed_pairing_or_geometry(field: str) -> None:
    payload = _view_payload()
    payload["walk_forward_method"] = None
    for other in ("walk_forward_hold_sharpe", "walk_forward_n_bars", "walk_forward_n_splits"):
        if other != field:
            payload.pop(other)
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(payload)


def test_direct_view_supports_legacy_omission_and_native_integral_geometry() -> None:
    measured = CrossSectionalView.model_validate(
        {
            **_view_payload(),
            "walk_forward_n_bars": np.int64(348),
            "walk_forward_n_splits": np.int32(3),
        }
    )
    assert type(measured.walk_forward_n_bars) is int
    assert type(measured.walk_forward_n_splits) is int
    legacy = _view_payload()
    for field in (
        "walk_forward_method",
        "walk_forward_hold_sharpe",
        "walk_forward_n_bars",
        "walk_forward_n_splits",
    ):
        legacy.pop(field)
    restored = CrossSectionalView.model_validate(legacy)
    assert restored.walk_forward_method is None
    assert restored.trials[0].walk_forward_oos_sharpe == 0.0


@pytest.mark.parametrize(
    "change",
    [
        {"walk_forward_hold_sharpe": None},
        {"lifetime_trials": 0},
    ],
)
def test_projection_reconstructs_unchecked_source_copies(change: dict[str, Any]) -> None:
    forged = _experiment().model_copy(update=change)
    with pytest.raises(ValidationError):
        _view(forged)


def test_projection_reconstructs_forged_nested_trial_before_primary_projection() -> None:
    experiment = _experiment()
    forged_trial = experiment.trials[0].model_copy(update={"observed_sharpe": float("nan")})
    forged = experiment.model_copy(update={"trials": [forged_trial, experiment.trials[1]]})
    with pytest.raises(ValidationError):
        _view(forged)


@pytest.mark.parametrize(
    "change",
    [
        {"walk_forward_hold_sharpe": float("nan")},
        {"walk_forward_hold_sharpe": float("inf")},
        {"walk_forward_n_bars": 348.0},
        {"walk_forward_n_splits": True},
    ],
)
def test_public_view_revalidation_refuses_unchecked_statistic_and_geometry_copies(
    change: dict[str, Any],
) -> None:
    measured = CrossSectionalView.model_validate(_view_payload())
    forged = measured.model_copy(update=change)
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(forged)
