"""ADR-349 compatibility preparation; actual Alpha9 remains unmeasured."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_high_purged_readers import high_evidence, high_trial, mixed

from app.api.v1.cross_sectional import CrossSectionalView, _view
from app.research.cross_sectional import purged, registry
from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import (
    InMemoryCrossSectionalStore,
    JsonFileCrossSectionalStore,
)
from app.research.cross_sectional.strategies import alpha9_signal

ALPHA_METHOD = "restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3"


def panel() -> pd.DataFrame:
    t = np.arange(80, dtype=float)
    return pd.DataFrame({str(i): 100 + t / 5 + np.sin(t / (i + 2) + i) for i in range(6)})


def evidence(**patch: Any) -> dict[str, Any]:
    return high_evidence(
        method=ALPHA_METHOD,
        dependency_rule="rolling-alpha9-v1",
        max_price_lag=11,
        embargo=11,
        **patch,
    )


def trial(**patch: Any) -> CrossSectionalTrial:
    data = {
        "strategy_name": "xs_alpha9",
        "parameters": {"window": 3, "quantile": 0.2},
        "purged_diagnostic": evidence(),
    }
    data.update(patch)
    return high_trial(**data)


def mixed_three_methods() -> CrossSectionalExperiment:
    original = mixed().model_dump()
    original["trials"].append(trial())
    original["strategy_names"].append("xs_alpha9")
    original["lifetime_trials"] = 4
    return CrossSectionalExperiment.model_validate(original)


def test_alpha9_factory_stable_identity_and_original_grid() -> None:
    a, b = registry.default_strategies(), registry.default_strategies()
    assert a["xs_alpha9"].build is b["xs_alpha9"].build
    assert a["xs_alpha9"].build is getattr(registry, "alpha9_factory", None)
    assert a["xs_alpha9"].param_grid == tuple({"window": w} for w in (3, 5, 10))


@pytest.mark.parametrize("window", [3, 5, 10, True, 3.9, np.int64(5)])
@pytest.mark.parametrize("q", [0.1, 0.2, 0.3])
def test_alpha9_factory_preserves_exact_signal_portfolio_and_early_trades(
    window: Any, q: float
) -> None:
    prices = panel()
    actual = registry.default_strategies()["xs_alpha9"].build({"window": window})(prices)
    expected = alpha9_signal(prices, int(window))
    pd.testing.assert_frame_equal(actual, expected, check_exact=True)
    pd.testing.assert_series_equal(
        portfolio_returns(actual, prices, quantile=q),
        portfolio_returns(expected, prices, quantile=q),
        check_exact=True,
    )
    if int(window) >= 3:
        np.testing.assert_array_equal(actual.iloc[1].to_numpy(), -prices.diff().iloc[1].to_numpy())
        assert portfolio_returns(actual, prices, quantile=q).iloc[1] < 0  # entry cost


def test_alpha9_factory_retains_lazy_lookup_and_mapping_capture() -> None:
    params: registry.Params = {}
    signal = registry.default_strategies()["xs_alpha9"].build(params)
    with pytest.raises(KeyError, match="window"):
        signal(panel())
    for w in (3, 10):
        params["window"] = w
        pd.testing.assert_frame_equal(signal(panel()), alpha9_signal(panel(), w), check_exact=True)
    del params["window"]
    with pytest.raises(KeyError, match="window"):
        signal(panel())


def test_alpha9_producer_is_still_unsupported_after_preparation() -> None:
    strategy = registry.default_strategies()["xs_alpha9"]
    assert purged.support_lag(strategy, [({"window": 5}, 0.2)], panel()) == (
        None,
        "unsupported_factory",
    )
    d, result = purged.measure_family_purged(
        strategy,
        [({"window": 5}, 0.1), ({"window": 5}, 0.3)],
        panel(),
        np.zeros((80, 2)),
        np.zeros(80),
        floor=0,
        requested_folds=3,
    )
    assert d.reason == "unsupported_factory" and result is None


@pytest.mark.parametrize("window", [3, 5, 10])
def test_alpha9_reader_binds_finalist_and_retains_v3(window: int) -> None:
    t = trial(parameters={"window": window, "quantile": 0.2})
    assert t.purged_diagnostic.method == ALPHA_METHOD
    assert CrossSectionalTrial.model_validate_json(t.model_dump_json()) == t


def test_alpha9_reader_preserves_no_fold_absence() -> None:
    data = evidence(
        status="no_usable_folds",
        n_bars=12,
        kept_fold_ordinals=(),
        mean_oos_sharpe=None,
        mean_oos_hold_sharpe=None,
    )
    assert (
        trial(
            purged_diagnostic=data, purged_cv_oos_sharpe=None
        ).purged_diagnostic.kept_fold_ordinals
        == ()
    )


@pytest.mark.parametrize(
    "patch",
    [
        {"method": "restricted-shift-family-purged-equal-weight-continuation-v1"},
        {"method": purged.HIGH_PURGED_METHOD},
        {"method": "unknown"},
        {"dependency_rule": "rolling-high-v1"},
        {"dependency_rule": "shifted-reversal-v1"},
        {"max_price_lag": 10, "embargo": 10},
        {"max_price_lag": 4.0},
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
def test_alpha9_reader_refuses_cross_method_rule_and_domain(patch: dict[str, Any]) -> None:
    data = evidence()
    data.update(patch)
    with pytest.raises(ValueError):
        purged.PurgedDiagnostic(**data)


@pytest.mark.parametrize(
    "patch",
    [
        {"strategy_name": "xs_52w_high"},
        {"strategy_name": "custom"},
        {"parameters": {"window": 4, "quantile": 0.2}},
        {"parameters": {"window": 3.0, "quantile": 0.2}},
        {"parameters": {"window": True, "quantile": 0.2}},
        {"parameters": {"window": 3, "quantile": 0.2, "skip": 0}},
        {
            "parameters": {"window": 10, "quantile": 0.2},
            "purged_diagnostic": high_evidence(
                method=ALPHA_METHOD, dependency_rule="rolling-alpha9-v1", max_price_lag=6, embargo=6
            ),
        },
        {"purged_cv_oos_sharpe": 0.0},
    ],
)
def test_alpha9_full_trial_refuses_family_finalist_or_scalar_forgery(patch: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        trial(**patch)


def test_alpha9_mixed_methods_revalidate_store_and_api(tmp_path: Path) -> None:
    experiment = mixed_three_methods()
    for store in (
        InMemoryCrossSectionalStore(),
        JsonFileCrossSectionalStore(tmp_path / "pool.json"),
    ):
        store.add(experiment)
        restored = store.all()[0]
        assert restored == experiment
        wire = _view(restored)
        assert wire.trials[-1].purged_diagnostic.method == ALPHA_METHOD
        assert CrossSectionalView.model_validate_json(wire.model_dump_json()) == wire
    bad = experiment.trials[-1].purged_diagnostic.model_copy(
        update={"dependency_rule": "rolling-high-v1"}
    )
    forged_trial = experiment.trials[-1].model_copy(update={"purged_diagnostic": bad})
    forged = experiment.model_copy(update={"trials": [*experiment.trials[:-1], forged_trial]})
    with pytest.raises(ValueError):
        _view(forged)
    with pytest.raises(ValueError):
        InMemoryCrossSectionalStore().add(forged)


@given(window=st.sampled_from([3, 5, 10]), lag=st.sampled_from([4, 6, 11]))
def test_alpha9_allocated_hull_includes_difference_and_previous_weight(
    window: int, lag: int
) -> None:
    data = evidence()
    data.update(max_price_lag=lag, embargo=lag)
    kwargs = {"parameters": {"window": window, "quantile": 0.2}, "purged_diagnostic": data}
    if lag < window + 1:
        with pytest.raises(ValueError):
            trial(**kwargs)
    else:
        assert trial(**kwargs).purged_diagnostic.max_price_lag >= window + 1
