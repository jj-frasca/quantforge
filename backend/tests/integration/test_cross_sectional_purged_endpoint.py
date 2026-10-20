"""ADR-327: publish stored family-local purged evidence without recomputation."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.v1.cross_sectional import (
    CrossSectionalTrialView,
    CrossSectionalView,
    _view,
    get_pool_path,
)
from app.main import app
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.lab.gate import GateConfig


def diagnostic(**changes: Any) -> dict[str, Any]:
    return {
        "method": "restricted-shift-family-purged-equal-weight-continuation-v1",
        "status": "measured",
        "n_bars": 100,
        "requested_folds": 5,
        "floor": 2,
        "dependency_rule": "shifted-reversal-v1",
        "max_price_lag": 6,
        "embargo": 6,
        "kept_fold_ordinals": [0, 1, 2, 3, 4],
        "mean_oos_sharpe": 0.0,
        "mean_oos_hold_sharpe": -0.25,
        **changes,
    }


def trial_payload(**changes: Any) -> dict[str, Any]:
    return {
        "strategy_name": "xs_reversal",
        "parameters": {"lookback": 5, "quantile": 0.2},
        "observed_sharpe": 0.2,
        "deflated_sharpe": -0.3,
        "pbo": 0.6,
        "parameter_stability_score": 0.7,
        "purged_cv_oos_sharpe": 0.0,
        "purged_diagnostic": diagnostic(),
        **changes,
    }


def experiment(day: int = 2) -> CrossSectionalExperiment:
    trials = [
        CrossSectionalTrial(**trial_payload()),
        CrossSectionalTrial(
            **trial_payload(
                strategy_name="xs_short_term_reversal_1m",
                parameters={"lookback": 63, "quantile": 0.2},
                purged_cv_oos_sharpe=-0.375,
                purged_diagnostic=diagnostic(
                    max_price_lag=64,
                    embargo=64,
                    kept_fold_ordinals=[0, 4],
                    mean_oos_sharpe=-0.375,
                    mean_oos_hold_sharpe=0.125,
                ),
            )
        ),
    ]
    return CrossSectionalExperiment(
        created_at=datetime(2026, 10, day, tzinfo=UTC),
        universe_symbols=["A", "B"],
        strategy_names=[t.strategy_name for t in trials],
        gate_config=GateConfig(),
        trials=trials,
        lifetime_trials=2,
    )


def view_payload() -> dict[str, Any]:
    return {
        "created_at": datetime(2026, 10, 2, tzinfo=UTC),
        "universe_size": 2,
        "best_strategy_name": None,
        "graduated": False,
        "graduate_holdout_sharpe": None,
        "trials": [trial_payload()],
    }


@pytest.fixture
def endpoint(tmp_path: Path) -> Iterator[tuple[TestClient, Path]]:
    pool = tmp_path / "pool.json"
    app.dependency_overrides[get_pool_path] = lambda: pool
    with TestClient(app) as client:
        try:
            yield client, pool
        finally:
            app.dependency_overrides.pop(get_pool_path, None)


def test_latest_measured_families_publish_exact_distinct_geometry_and_pairs(
    endpoint: tuple[TestClient, Path],
) -> None:
    client, pool = endpoint
    store = JsonFileCrossSectionalStore(pool)
    store.add(experiment(day=1))
    latest = experiment()
    store.add(latest)
    before = pool.read_bytes()
    response = client.get("/api/v1/cross-sectional")
    assert response.status_code == 200
    body = response.json()
    assert body["created_at"] == latest.model_dump(mode="json")["created_at"]
    for actual, expected in zip(body["trials"], latest.trials, strict=True):
        assert actual["purged_cv_oos_sharpe"] == expected.purged_cv_oos_sharpe
        assert actual["purged_diagnostic"] == expected.purged_diagnostic.model_dump(mode="json")
    assert pool.read_bytes() == before


@pytest.mark.parametrize("status", ["unsupported", "no_usable_folds"])
def test_current_unmeasured_statuses_publish_without_scores(
    status: str,
    endpoint: tuple[TestClient, Path],
) -> None:
    client, pool = endpoint
    data = experiment().model_dump(mode="json")
    for trial in data["trials"]:
        if status == "unsupported":
            evidence = {
                key: diagnostic()[key] for key in ("method", "n_bars", "requested_folds", "floor")
            }
            evidence.update(status=status, reason="unsupported_factory")
        else:
            evidence = {
                **trial["purged_diagnostic"],
                "status": status,
                "floor": 100,
                "embargo": 100,
                "kept_fold_ordinals": [],
                "mean_oos_sharpe": None,
                "mean_oos_hold_sharpe": None,
            }
        trial.update(purged_cv_oos_sharpe=None, purged_diagnostic=evidence)
    pool.write_text(json.dumps([data]))
    body = client.get("/api/v1/cross-sectional").json()
    assert all(t["purged_diagnostic"]["status"] == status for t in body["trials"])
    assert all(t["purged_cv_oos_sharpe"] is None for t in body["trials"])


@pytest.mark.parametrize("scalar", [None, -0.75, 0.0])
def test_legacy_omission_null_and_unpaired_scores(
    scalar: float | None,
    endpoint: tuple[TestClient, Path],
) -> None:
    client, pool = endpoint
    data = experiment().model_dump(mode="json")
    for trial in data["trials"]:
        trial.pop("purged_diagnostic")
        trial.pop("purged_cv_oos_sharpe")
    data["trials"][0]["purged_cv_oos_sharpe"] = scalar
    pool.write_text(json.dumps([data]))
    body = client.get("/api/v1/cross-sectional").json()
    assert [t["purged_cv_oos_sharpe"] for t in body["trials"]] == [scalar, None]
    assert all(t["purged_diagnostic"] is None for t in body["trials"])


@pytest.mark.parametrize(
    "changes",
    [
        {"method": "unknown"},
        {"status": "unknown"},
        {"n_bars": True},
        {"n_bars": 100.0},
        {"requested_folds": "5"},
        {"floor": False},
        {"mean_oos_sharpe": float("nan")},
        {"mean_oos_hold_sharpe": float("inf")},
        {"mean_oos_hold_sharpe": None},
        {"embargo": 5},
        {"kept_fold_ordinals": [0, 1, 2, 3]},
        {"kept_fold_ordinals": [0, 1, 2, 3, 3]},
        {"status": "no_usable_folds"},
        {"status": "unsupported", "reason": "unsupported_factory"},
    ],
)
def test_direct_trial_refuses_malformed_nested_evidence(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        CrossSectionalTrialView.model_validate(
            trial_payload(purged_diagnostic=diagnostic(**changes))
        )


@pytest.mark.parametrize("scalar", [None, 0.25, float("nan"), float("inf")])
def test_trial_scalar_must_bind_measured_mean(scalar: float | None) -> None:
    with pytest.raises(ValidationError):
        CrossSectionalTrialView.model_validate(trial_payload(purged_cv_oos_sharpe=scalar))


@pytest.mark.parametrize("scalar", [float("nan"), float("inf"), -float("inf")])
def test_legacy_unpaired_scalar_still_requires_finite_evidence(scalar: float) -> None:
    with pytest.raises(ValidationError):
        CrossSectionalTrialView.model_validate(
            trial_payload(purged_diagnostic=None, purged_cv_oos_sharpe=scalar)
        )


def test_current_unmeasured_cannot_carry_scalar() -> None:
    evidence = diagnostic(
        status="no_usable_folds",
        floor=100,
        embargo=100,
        kept_fold_ordinals=[],
        mean_oos_sharpe=None,
        mean_oos_hold_sharpe=None,
    )
    with pytest.raises(ValidationError):
        CrossSectionalTrialView.model_validate(trial_payload(purged_diagnostic=evidence))


@pytest.mark.parametrize(
    "change",
    [
        None,
        {"floor": 3},
        {"n_bars": 101},
        {"requested_folds": 4, "kept_fold_ordinals": [0, 1, 2, 3]},
    ],
)
def test_view_requires_complete_same_request_evidence(change: dict[str, Any] | None) -> None:
    payload = view_payload()
    payload["trials"].append(
        trial_payload(purged_diagnostic=None if change is None else diagnostic(**change))
    )
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(payload)


def test_attributed_walk_forward_bars_bind_purged_bars() -> None:
    payload = view_payload()
    payload.update(
        walk_forward_method="family-walk-forward-equal-weight-continuation-v1",
        walk_forward_n_bars=101,
        walk_forward_n_splits=3,
        walk_forward_hold_sharpe=0.1,
    )
    payload["trials"][0]["walk_forward_oos_sharpe"] = 0.2
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(payload)
    payload["walk_forward_n_bars"] = 100
    assert CrossSectionalView.model_validate(payload).walk_forward_n_bars == 100


def test_unchecked_trial_and_root_copies_revalidate_nested_evidence() -> None:
    view = CrossSectionalView.model_validate(view_payload())
    trial = view.trials[0]
    evidence = trial.purged_diagnostic
    assert evidence is not None
    forged_trial = trial.model_copy(
        update={
            "purged_diagnostic": evidence.model_copy(update={"mean_oos_hold_sharpe": float("inf")})
        }
    )
    with pytest.raises(ValidationError):
        CrossSectionalTrialView.model_validate(forged_trial)
    with pytest.raises(ValidationError):
        CrossSectionalView.model_validate(view.model_copy(update={"trials": [forged_trial]}))


def test_projection_preserves_stronger_source_finalist_domain_refusal() -> None:
    source = experiment()
    forged = source.trials[0].model_copy(update={"parameters": {"lookback": 63, "quantile": 0.2}})
    with pytest.raises(ValidationError):
        _view(source.model_copy(update={"trials": [forged, source.trials[1]]}))


def test_huge_wire_geometry_reuses_allocation_free_native_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> Any:
        pytest.fail("wire validation allocated geometry arrays")

    monkeypatch.setattr(np, "arange", forbidden)
    n = 10**100
    payload = view_payload()
    payload["trials"][0]["purged_diagnostic"] = diagnostic(
        n_bars=n,
        requested_folds=n,
        floor=n - 2,
        embargo=n - 2,
        kept_fold_ordinals=[0, n - 1],
    )
    evidence = CrossSectionalView.model_validate(payload).trials[0].purged_diagnostic
    assert evidence is not None and evidence.kept_fold_ordinals == (0, n - 1)
