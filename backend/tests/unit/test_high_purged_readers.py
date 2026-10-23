"""ADR-347 reader compatibility; no high-proximity producer is enabled."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional.purged import PurgedDiagnostic
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.lab.gate import GateConfig

HIGH_METHOD = "restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2"
SHIFT_METHOD = "restricted-shift-family-purged-equal-weight-continuation-v1"


def high_evidence(**patch: Any) -> dict[str, Any]:
    data = {
        "method": HIGH_METHOD,
        "status": "measured",
        "n_bars": 900,
        "requested_folds": 3,
        "floor": 0,
        "dependency_rule": "rolling-high-v1",
        "max_price_lag": 252,
        "embargo": 252,
        "kept_fold_ordinals": (0, 1, 2),
        "mean_oos_sharpe": -0.25,
        "mean_oos_hold_sharpe": 0.5,
    }
    data.update(patch)
    return data


def high_trial(**patch: Any) -> CrossSectionalTrial:
    data = {
        "strategy_name": "xs_52w_high",
        "parameters": {"window": 126, "quantile": 0.2},
        "observed_sharpe": 1.0,
        "deflated_sharpe": 0.5,
        "pbo": 0.1,
        "parameter_stability_score": 0.5,
        "purged_cv_oos_sharpe": -0.25,
        "purged_diagnostic": high_evidence(),
        "walk_forward_oos_sharpe": 0.3,
    }
    data.update(patch)
    return CrossSectionalTrial(**data)


def mixed() -> CrossSectionalExperiment:
    shift = high_evidence(
        method=SHIFT_METHOD,
        dependency_rule="shifted-reversal-v1",
        max_price_lag=6,
        embargo=6,
        mean_oos_sharpe=0.0,
    )
    other = high_trial(
        strategy_name="xs_reversal",
        parameters={"lookback": 5, "quantile": 0.2},
        purged_diagnostic=shift,
        purged_cv_oos_sharpe=0.0,
    )
    unsupported = high_trial(
        strategy_name="xs_value",
        parameters={"quantile": 0.2},
        purged_cv_oos_sharpe=None,
        purged_diagnostic={
            "method": SHIFT_METHOD,
            "status": "unsupported",
            "n_bars": 900,
            "requested_folds": 3,
            "floor": 0,
            "reason": "unsupported_factory",
        },
    )
    return CrossSectionalExperiment(
        created_at=datetime(2026, 10, 22, tzinfo=UTC),
        universe_symbols=["A", "B", "C"],
        strategy_names=["xs_52w_high", "xs_reversal", "xs_value"],
        trials=[high_trial(), other, unsupported],
        lifetime_trials=3,
        gate_config=GateConfig(),
        walk_forward_method="family-walk-forward-equal-weight-continuation-v1",
        walk_forward_hold_sharpe=0.1,
        walk_forward_n_bars=900,
        walk_forward_n_splits=3,
    )


@pytest.mark.parametrize("window", [126, 189, 252])
def test_high_reader_retains_exact_method_and_finalist(window: int) -> None:
    trial = high_trial(parameters={"window": window, "quantile": 0.2})
    assert trial.purged_diagnostic is not None
    assert trial.purged_diagnostic.method == HIGH_METHOD
    assert CrossSectionalTrial.model_validate_json(trial.model_dump_json()) == trial


def test_high_reader_no_fold_geometry_is_not_a_zero_measurement() -> None:
    data = high_evidence(
        status="no_usable_folds",
        n_bars=300,
        kept_fold_ordinals=(),
        mean_oos_sharpe=None,
        mean_oos_hold_sharpe=None,
    )
    trial = high_trial(purged_diagnostic=data, purged_cv_oos_sharpe=None)
    assert trial.purged_diagnostic is not None
    assert trial.purged_diagnostic.kept_fold_ordinals == ()


@pytest.mark.parametrize(
    "patch",
    [
        {"method": SHIFT_METHOD},
        {"method": "unknown"},
        {"dependency_rule": "shifted-reversal-v1"},
        {"dependency_rule": "shifted-momentum-v1"},
        {"dependency_rule": None},
        {"max_price_lag": 127, "embargo": 127},
        {"max_price_lag": True},
        {"max_price_lag": 252.0},
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
        {"mean_oos_sharpe": np.nan},
        {"kept_fold_ordinals": (0, 2)},
        {"embargo": 251},
    ],
)
def test_high_reader_rejects_method_rule_or_geometry_forgery(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        PurgedDiagnostic(**high_evidence(**patch))


@pytest.mark.parametrize(
    "patch",
    [
        {"strategy_name": "xs_reversal", "parameters": {"lookback": 5, "quantile": 0.2}},
        {"strategy_name": "custom"},
        {"parameters": {"window": 125, "quantile": 0.2}},
        {"parameters": {"window": True, "quantile": 0.2}},
        {"parameters": {"window": 126.0, "quantile": 0.2}},
        {"parameters": {"window": 126, "quantile": 0.2, "skip": 0}},
        {"parameters": {"window": 126}},
        {"purged_cv_oos_sharpe": 0.0},
        {
            "parameters": {"window": 252, "quantile": 0.2},
            "purged_diagnostic": high_evidence(max_price_lag=126, embargo=126),
        },
    ],
)
def test_high_trial_refuses_wrong_family_finalist_or_scalar(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        high_trial(**patch)


def test_mixed_methods_roundtrip_store_and_api_preserve_pairing(tmp_path: Path) -> None:
    experiment = mixed()
    for store in (
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ):
        store.add(experiment)
        restored = store.all()[0]
        assert restored == experiment
        view = _view(restored)
        assert CrossSectionalView.model_validate_json(view.model_dump_json()) == view
        assert [t.purged_cv_oos_sharpe for t in view.trials] == [-0.25, 0.0, None]
        assert view.trials[0].purged_diagnostic is not None
        assert view.trials[0].purged_diagnostic.method == HIGH_METHOD
        assert view.trials[1].purged_diagnostic is not None
        assert view.trials[1].purged_diagnostic.method == SHIFT_METHOD
    assert experiment.trials[0].purged_diagnostic is not None
    with pytest.raises(ValueError):
        experiment.trials[0].purged_diagnostic.embargo = 1


@pytest.mark.parametrize("field,value", [("n_bars", 901), ("requested_folds", 2), ("floor", 1)])
def test_mixed_methods_keep_common_request_refusals(field: str, value: int) -> None:
    original = mixed()
    for original_data, model in (
        (original.model_dump(), CrossSectionalExperiment),
        (_view(original).model_dump(), CrossSectionalView),
    ):
        original_data["trials"][0]["purged_diagnostic"][field] = value
        # Isolate the common-request check from the separately tested WF binding.
        original_data["walk_forward_method"] = None
        original_data["walk_forward_hold_sharpe"] = None
        original_data["walk_forward_n_bars"] = None
        original_data["walk_forward_n_splits"] = None
        if field == "requested_folds":
            original_data["trials"][0]["purged_diagnostic"]["kept_fold_ordinals"] = (0, 1)
        with pytest.raises(ValueError, match="same request geometry"):
            model.model_validate(original_data)


@pytest.mark.parametrize("target", ["missing", "wf", "scalar", "unchecked_rule"])
def test_mixed_methods_revalidate_whole_graph_and_api(target: str) -> None:
    experiment = mixed()
    data = experiment.model_dump()
    if target == "missing":
        data["trials"][0]["purged_diagnostic"] = None
    elif target == "wf":
        data["walk_forward_n_bars"] = 901
    elif target == "scalar":
        data["trials"][0]["purged_cv_oos_sharpe"] = 0.0
    else:
        bad_evidence = experiment.trials[0].purged_diagnostic.model_copy(
            update={"dependency_rule": "shifted-reversal-v1"}
        )
        bad_trial = experiment.trials[0].model_copy(update={"purged_diagnostic": bad_evidence})
        forged = experiment.model_copy(update={"trials": [bad_trial, *experiment.trials[1:]]})
        with pytest.raises(ValueError):
            InMemoryCrossSectionalStore().add(forged)
        with pytest.raises(ValueError):
            _view(forged)
        return
    with pytest.raises(ValueError):
        CrossSectionalExperiment.model_validate(data)
    wire = _view(experiment).model_dump()
    if target == "wf":
        wire["walk_forward_n_bars"] = 901
    else:
        wire["trials"][0][
            "purged_diagnostic" if target == "missing" else "purged_cv_oos_sharpe"
        ] = None if target == "missing" else 0.0
    with pytest.raises(ValueError):
        CrossSectionalView.model_validate(wire)


@given(window=st.sampled_from([126, 189, 252]), maximum=st.sampled_from([126, 189, 252]))
def test_high_reader_allocated_hull_covers_finalist(window: int, maximum: int) -> None:
    kwargs = {
        "parameters": {"window": window, "quantile": 0.2},
        "purged_diagnostic": high_evidence(max_price_lag=maximum, embargo=maximum),
    }
    if maximum < window:
        with pytest.raises(ValueError):
            high_trial(**kwargs)
    else:
        assert high_trial(**kwargs).purged_diagnostic.max_price_lag >= window


def test_high_reader_preserves_inherited_parameter_normalization() -> None:
    # Trial's existing float|int union projects a NumPy integer to float. Match
    # the shifted-family post-normalization policy instead of changing that union.
    with pytest.raises(ValueError, match="purged finalist window"):
        high_trial(parameters={"window": np.int64(126), "quantile": 0.2})
    assert PurgedDiagnostic(**high_evidence(max_price_lag=np.int64(252))).max_price_lag == 252
