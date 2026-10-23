"""ADR-352 attributed Alpha4 readers; producer domains are governed by ADR-353."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_alpha9_purged_readers import mixed_three_methods, panel
from tests.unit.test_high_purged_readers import high_evidence, high_trial

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional import purged, registry
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)

ALPHA4_METHOD = (
    "restricted-pandas-3.0.6-numpy-2.5.4-cython-alpha4-purged-equal-weight-continuation-v4"
)


def evidence(**patch: Any) -> dict[str, Any]:
    data = high_evidence(
        method=ALPHA4_METHOD,
        dependency_rule="rolling-alpha4-percentile-v1",
        max_price_lag=21,
        embargo=21,
    )
    data.update(patch)
    return data


def trial(**patch: Any) -> CrossSectionalTrial:
    data = {
        "strategy_name": "xs_alpha4",
        "parameters": {"window": 5, "quantile": 0.2},
        "purged_diagnostic": evidence(),
    }
    data.update(patch)
    return high_trial(**data)


def mixed_four() -> CrossSectionalExperiment:
    data = mixed_three_methods().model_dump()
    data["trials"].append(trial())
    data["strategy_names"].append("xs_alpha4")
    data["lifetime_trials"] = 5
    return CrossSectionalExperiment.model_validate(data)


@pytest.mark.parametrize("window", [5, 9, 21])
def test_alpha4_attributed_reader_binds_shipped_finalist(window: int) -> None:
    item = trial(parameters={"window": window, "quantile": 0.2})
    assert item.purged_diagnostic is not None
    assert item.purged_diagnostic.method == ALPHA4_METHOD
    assert CrossSectionalTrial.model_validate_json(item.model_dump_json()) == item


def test_alpha4_no_fold_absence_is_not_a_zero_score() -> None:
    item = trial(
        purged_cv_oos_sharpe=None,
        purged_diagnostic=evidence(
            status="no_usable_folds",
            n_bars=24,
            kept_fold_ordinals=(),
            mean_oos_sharpe=None,
            mean_oos_hold_sharpe=None,
        ),
    )
    assert item.purged_diagnostic is not None
    assert item.purged_diagnostic.kept_fold_ordinals == ()


@pytest.mark.parametrize(
    "patch",
    [
        {"method": "restricted-shift-family-purged-equal-weight-continuation-v1"},
        {"method": purged.HIGH_PURGED_METHOD},
        {"method": purged.ALPHA9_PURGED_METHOD},
        {"method": "unknown"},
        {"dependency_rule": "rolling-high-v1"},
        {"dependency_rule": "rolling-alpha9-v1"},
        {"dependency_rule": "shifted-reversal-v1"},
        {"max_price_lag": 10, "embargo": 10},
        {"max_price_lag": 5.0},
        {"max_price_lag": True},
        {"n_bars": 900.0},
        {"requested_folds": True},
        {"floor": 0.0},
        {"mean_oos_sharpe": float("inf")},
        {"mean_oos_hold_sharpe": float("nan")},
        {"embargo": 20},
        {"kept_fold_ordinals": (0, 2)},
        {"kept_fold_ordinals": (0, 1, 1)},
        {"status": "no_usable_folds"},
        {
            "status": "unsupported",
            "reason": "unsupported_factory",
            "dependency_rule": None,
            "max_price_lag": None,
            "embargo": None,
            "kept_fold_ordinals": None,
            "mean_oos_sharpe": None,
            "mean_oos_hold_sharpe": None,
        },
    ],
)
def test_alpha4_reader_refuses_forged_domain_or_geometry(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        purged.PurgedDiagnostic(**evidence(**patch))


@pytest.mark.parametrize(
    "patch",
    [
        {"strategy_name": "xs_52w_high"},
        {"strategy_name": "xs_alpha9"},
        {"strategy_name": "custom"},
        {"parameters": {"window": 3, "quantile": 0.2}},
        {"parameters": {"window": 5.0, "quantile": 0.2}},
        {"parameters": {"window": True, "quantile": 0.2}},
        {"parameters": {"window": np.int64(5), "quantile": 0.2}},
        {"parameters": {"window": 5, "quantile": 0.2, "skip": 0}},
        {"parameters": {"quantile": 0.2}},
        {"purged_cv_oos_sharpe": 0.0},
        {
            "parameters": {"window": 21, "quantile": 0.2},
            "purged_diagnostic": evidence(max_price_lag=9, embargo=9),
        },
    ],
)
def test_alpha4_full_trial_refuses_family_finalist_scalar_forgery(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        trial(**patch)


def test_alpha4_mixed_four_method_store_api_and_immutable_claims(tmp_path: Path) -> None:
    exp = mixed_four()
    stores: list[InMemoryCrossSectionalStore | JsonFileCrossSectionalStore] = [
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ]
    for store in stores:
        store.add(exp)
        restored = store.all()[0]
        assert restored == exp
        wire = _view(restored)
        assert wire.trials[-1].purged_diagnostic is not None
        assert wire.trials[-1].purged_diagnostic.method == ALPHA4_METHOD
        assert CrossSectionalView.model_validate_json(wire.model_dump_json()) == wire
    diag = exp.trials[-1].purged_diagnostic
    assert diag is not None
    with pytest.raises(ValueError):
        diag.embargo = 0  # type: ignore[misc]  # exercise frozen-model assignment
    with pytest.raises(TypeError):
        exp.trials[-1].parameters["window"] = 21
    bad = diag.model_copy(update={"dependency_rule": "rolling-alpha9-v1"})
    bad_trial = exp.trials[-1].model_copy(update={"purged_diagnostic": bad})
    forged = exp.model_copy(update={"trials": [*exp.trials[:-1], bad_trial]})
    forged_stores: list[InMemoryCrossSectionalStore | JsonFileCrossSectionalStore] = [
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "bad.json"),
    ]
    for store in forged_stores:
        with pytest.raises(ValueError):
            store.add(forged)
    with pytest.raises(ValueError):
        _view(forged)


@pytest.mark.parametrize("target", ["bars", "folds", "floor", "missing", "wf", "scalar"])
def test_alpha4_mixed_claims_preserve_common_request_wf_and_scalar_binding(target: str) -> None:
    data = mixed_four().model_dump()
    if target == "wf":
        data["walk_forward_n_bars"] = 901
    elif target == "missing":
        data["trials"][-1]["purged_diagnostic"] = None
    elif target == "scalar":
        data["trials"][-1]["purged_cv_oos_sharpe"] = 0.0
    else:
        diag = data["trials"][-1]["purged_diagnostic"]
        if target == "bars":
            diag["n_bars"] = 901
            for field in (
                "walk_forward_method",
                "walk_forward_hold_sharpe",
                "walk_forward_n_bars",
                "walk_forward_n_splits",
            ):
                data[field] = None
        elif target == "folds":
            diag["requested_folds"] = 2
            diag["kept_fold_ordinals"] = (0, 1)
        else:
            diag["floor"] = 1
    with pytest.raises(ValueError):
        CrossSectionalExperiment.model_validate(data)


def test_alpha4_actual_producer_refuses_unaudited_numpy() -> None:
    # ADR-353 supersedes the blanket refusal with a dedicated unaudited-domain check.
    receipt = purged.Alpha4Runtime("3.0.6", "unaudited", False)
    strategy = registry.default_strategies()["xs_alpha4"]
    configs: list[tuple[registry.Params, float]] = [({"window": 5}, 0.1), ({"window": 21}, 0.3)]
    assert purged.support_lag(strategy, configs, panel(), alpha4_runtime=receipt) == (
        None,
        "unsupported_numpy_version",
    )
    diag, result = purged.measure_family_purged(
        strategy,
        configs,
        panel(),
        np.zeros((80, 2)),
        np.zeros(80),
        floor=0,
        requested_folds=3,
        alpha4_runtime=receipt,
    )
    assert diag.reason == "unsupported_numpy_version" and result is None
    assert diag.method.endswith("continuation-v1")


@given(window=st.sampled_from([5, 9, 21]), lag=st.sampled_from([5, 9, 21]))
def test_alpha4_allocated_lag_covers_finalist(window: int, lag: int) -> None:
    data = {
        "parameters": {"window": window, "quantile": 0.2},
        "purged_diagnostic": evidence(max_price_lag=lag, embargo=lag),
    }
    if lag < window:
        with pytest.raises(ValueError):
            trial(**data)
    else:
        item = trial(**data)
        assert item.purged_diagnostic is not None and item.purged_diagnostic.max_price_lag == lag
