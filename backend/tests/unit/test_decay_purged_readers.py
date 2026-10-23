"""ADR-355 attributed decay readers; actual producer remains unsupported."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_alpha4_purged_readers import mixed_four
from tests.unit.test_alpha9_purged_readers import panel
from tests.unit.test_high_purged_readers import high_evidence, high_trial

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional import purged, registry
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)

DECAY_METHOD = (
    "restricted-pandas-3.0.6-numpy-2.5.4-cython-decay-reversal-purged-equal-weight-continuation-v5"
)


def evidence(**patch: Any) -> dict[str, Any]:
    data = high_evidence(
        method=DECAY_METHOD,
        dependency_rule="rolling-decay-reversal-v1",
        max_price_lag=11,
        embargo=11,
    )
    data.update(patch)
    return data


def trial(**patch: Any) -> CrossSectionalTrial:
    data = {
        "strategy_name": "xs_decay_reversal",
        "parameters": {"window": 5, "quantile": 0.2},
        "purged_diagnostic": evidence(),
    }
    data.update(patch)
    return high_trial(**data)


def mixed_five() -> CrossSectionalExperiment:
    data = mixed_four().model_dump()
    data["trials"].append(trial())
    data["strategy_names"].append("xs_decay_reversal")
    data["lifetime_trials"] = 6
    return CrossSectionalExperiment.model_validate(data)


@pytest.mark.parametrize("window", [3, 5, 10])
def test_decay_attributed_reader_binds_shipped_finalist(window: int) -> None:
    item = trial(parameters={"window": window, "quantile": 0.2})
    assert item.purged_diagnostic is not None
    assert item.purged_diagnostic.method == DECAY_METHOD
    assert CrossSectionalTrial.model_validate_json(item.model_dump_json()) == item


def test_decay_no_fold_absence_is_not_a_zero_score() -> None:
    item = trial(
        purged_cv_oos_sharpe=None,
        purged_diagnostic=evidence(
            status="no_usable_folds",
            n_bars=12,
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
        {"method": purged.ALPHA4_PURGED_METHOD},
        {"method": "unknown"},
        {"dependency_rule": "rolling-high-v1"},
        {"dependency_rule": "rolling-alpha9-v1"},
        {"dependency_rule": "rolling-alpha4-percentile-v1"},
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
def test_decay_reader_refuses_forged_domain_or_geometry(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        purged.PurgedDiagnostic(**evidence(**patch))


@pytest.mark.parametrize(
    "patch",
    [
        {"strategy_name": "xs_52w_high"},
        {"strategy_name": "xs_alpha9"},
        {"strategy_name": "custom"},
        {"parameters": {"window": 2, "quantile": 0.2}},
        {"parameters": {"window": 5.0, "quantile": 0.2}},
        {"parameters": {"window": True, "quantile": 0.2}},
        {"parameters": {"window": np.int64(5), "quantile": 0.2}},
        {"parameters": {"window": 5, "quantile": 0.2, "skip": 0}},
        {"parameters": {"quantile": 0.2}},
        {"purged_cv_oos_sharpe": 0.0},
        {
            "parameters": {"window": 10, "quantile": 0.2},
            "purged_diagnostic": evidence(max_price_lag=6, embargo=6),
        },
    ],
)
def test_decay_full_trial_refuses_family_finalist_scalar_forgery(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        trial(**patch)


def test_decay_mixed_five_method_store_api_and_immutable_claims(tmp_path: Path) -> None:
    exp = mixed_five()
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
        assert wire.trials[-1].purged_diagnostic.method == DECAY_METHOD
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
def test_decay_mixed_claims_preserve_common_request_wf_and_scalar_binding(target: str) -> None:
    data = mixed_five().model_dump()
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


def test_decay_actual_producer_stays_unsupported() -> None:
    strategy = registry.default_strategies()["xs_decay_reversal"]
    configs: list[tuple[registry.Params, float]] = [({"window": 3}, 0.1), ({"window": 10}, 0.3)]
    assert purged.support_lag(strategy, configs, panel()) == (None, "unsupported_factory")
    diag, result = purged.measure_family_purged(
        strategy,
        configs,
        panel(),
        np.zeros((80, 2)),
        np.zeros(80),
        floor=0,
        requested_folds=3,
    )
    assert diag.reason == "unsupported_factory" and result is None
    assert diag.method.endswith("continuation-v1") and diag.max_price_lag is None


@given(window=st.sampled_from([3, 5, 10]), lag=st.sampled_from([4, 6, 11]))
def test_decay_allocated_lag_covers_finalist(window: int, lag: int) -> None:
    data = {
        "parameters": {"window": window, "quantile": 0.2},
        "purged_diagnostic": evidence(max_price_lag=lag, embargo=lag),
    }
    if lag < window + 1:
        with pytest.raises(ValueError):
            trial(**data)
    else:
        item = trial(**data)
        assert item.purged_diagnostic is not None and item.purged_diagnostic.max_price_lag == lag


@pytest.mark.parametrize(
    "method,rule,lag",
    [
        (purged.ALPHA9_PURGED_METHOD, "rolling-decay-reversal-v1", 11),
        (DECAY_METHOD, "rolling-alpha9-v1", 11),
        (purged.ALPHA4_PURGED_METHOD, "rolling-decay-reversal-v1", 21),
    ],
)
def test_decay_symmetric_method_rule_binding(method: str, rule: str, lag: int) -> None:
    with pytest.raises(ValueError):
        purged.PurgedDiagnostic(
            **evidence(method=method, dependency_rule=rule, max_price_lag=lag, embargo=lag)
        )


def test_decay_exported_constant_exact_identity() -> None:
    assert getattr(purged, "DECAY_PURGED_METHOD", None) == DECAY_METHOD
