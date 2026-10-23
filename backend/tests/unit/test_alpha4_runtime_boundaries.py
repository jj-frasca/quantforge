"""ADR353 receipt boundaries beyond the initial producer RED controls."""

import numpy as np
import pytest
from tests.unit.test_alpha4_purged_producer import measure, runtime
from tests.unit.test_high_purged_producer import panel

from app.research.cross_sectional import purged
from app.research.cross_sectional.registry import default_strategies


def test_alpha4_capture_unknown_pandas_does_not_inspect_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(purged.pd, "__version__", "unaudited")
    monkeypatch.setattr(
        purged.pd, "get_option", lambda *a: pytest.fail("unknown dispatch inspected")
    )
    assert purged.capture_alpha4_runtime() == runtime("unaudited", np.__version__, None)


def test_alpha4_old_high_slot_cannot_supply_numpy_identity() -> None:
    p = panel(300)
    with pytest.raises(ValueError, match="runtime receipt"):
        purged.measure_family_purged(
            default_strategies()["xs_alpha4"],
            [({"window": 5}, 0.1), ({"window": 5}, 0.3)],
            p,
            np.zeros((300, 2)),
            np.zeros(300),
            floor=0,
            requested_folds=3,
            high_runtime=purged.HighRuntime("3.0.6", False),
        )


def test_alpha4_supported_original_numpy_integral_and_empty_allocation() -> None:
    strategy = default_strategies()["xs_alpha4"]
    assert purged.support_lag(strategy, [({"window": np.int64(5)}, 0.2)], panel()) == (5, None)
    assert purged.support_lag(strategy, [], panel()) == (None, "unsupported_parameters")


@pytest.mark.parametrize("floor", [-1, True, 1.5, np.bool_(False)])
def test_alpha4_original_invalid_floor_refuses_before_receipt(floor: object) -> None:
    with pytest.raises((ValueError, TypeError), match="embargo"):
        measure(floor=floor, receipt=runtime())


def test_alpha4_partial_kept_folds_have_actual_paired_control() -> None:
    from app.research.backtesting.metrics import sharpe_ratio
    from app.research.cross_sectional.engine import asset_returns
    from app.validation.purged_cv import purged_kfold_splits

    evidence, result = measure(floor=110, receipt=runtime())
    assert result is not None and evidence.kept_fold_ordinals == (0, 2)
    benchmark = asset_returns(panel(300)).mean(axis=1)
    splits = purged_kfold_splits(300, 3, 110)
    expected = np.mean([sharpe_ratio(benchmark.iloc[splits[j][1]]) for j in (0, 2)])
    assert evidence.mean_oos_hold_sharpe == expected


def test_alpha4_wrong_support_receipt_refuses_without_live_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        purged,
        "capture_alpha4_runtime",
        lambda: pytest.fail("wrong receipt fallback"),
        raising=False,
    )
    with pytest.raises(ValueError, match="runtime receipt"):
        purged.support_lag(
            default_strategies()["xs_alpha4"],
            [({"window": 5}, 0.2)],
            panel(),
            alpha4_runtime=purged.HighRuntime("3.0.6", False),
        )


def test_alpha4_holdout_tail_does_not_enter_fold_measurements() -> None:
    from app.research.cross_sectional.search import run_cross_sectional_search
    from app.research.lab.gate import GateConfig

    source = panel(780)
    changed = source.copy()
    changed.iloc[528:] *= np.linspace(1, 2, 252)[:, None]

    def claims(prices):
        experiment = run_cross_sectional_search(
            prices,
            ["xs_alpha4"],
            quantiles=(0.1, 0.3),
            config=GateConfig(trial_budget=6),
            purged_folds=3,
        )
        return experiment.trials[0].purged_diagnostic

    first, second = claims(source), claims(changed)
    assert first == second and first.status == "measured"
    assert first.n_bars == 528


@pytest.mark.parametrize("replacement", ["factory", "name"])
def test_alpha4_custom_substitutions_do_not_capture(
    replacement: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    from app.research.cross_sectional import search
    from app.research.lab.gate import GateConfig

    original_registry = default_strategies

    def registry(*args, **kwargs):
        entries = original_registry(*args, **kwargs)
        alpha = entries["xs_alpha4"]
        entries["xs_alpha4"] = replace(
            alpha,
            **(
                {"build": lambda p: alpha.build(p)}
                if replacement == "factory"
                else {"name": "custom_alpha4"}
            ),
        )
        return entries

    monkeypatch.setattr(search, "default_strategies", registry)
    monkeypatch.setattr(search, "capture_alpha4_runtime", lambda: pytest.fail("custom captured"))

    def run():
        return search.run_cross_sectional_search(
            panel(),
            ["xs_alpha4"],
            quantiles=(0.1, 0.3),
            config=GateConfig(trial_budget=6),
            purged_folds=3,
        )

    if replacement == "name":
        # Existing final identity validation refuses an internally inconsistent registry.
        with pytest.raises(ValueError, match="best_strategy_name"):
            run()
    else:
        assert run().trials[0].purged_diagnostic.reason == "unsupported_factory"
