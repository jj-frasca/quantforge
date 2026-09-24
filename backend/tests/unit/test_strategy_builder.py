"""Builder: validated configs construct the right concrete BaseStrategy; the
build_strategy_from_dict path round-trips through Pydantic and surfaces validation
errors on unknown names or invalid params."""

import pytest
from pydantic import ValidationError

from app.research.strategies.builder import build_strategy, build_strategy_from_dict
from app.research.strategies.catalog import STRATEGY_CATALOG
from app.research.strategies.configs import SMAConfig
from app.research.strategies.sma import SMAStrategy


def test_build_strategy_dispatches_each_config_variant() -> None:
    # Smoke: every catalog discriminator can be constructed via build_strategy. Any
    # missing branch here is the moment ADR-010's promise breaks for /validate.
    #
    # Driven off STRATEGY_CATALOG (not a hand-maintained literal list, FINDING-053/ADR-125): a
    # hardcoded list here stopped growing after the 11th strategy (2026-06-06) while 23 more were
    # added since, so this test silently stopped exercising most of build_strategy's isinstance
    # chain despite its own comment claiming to be the backstop for exactly that regression.
    # build_strategy_from_dict({}) relies on each config's defaults being valid, which
    # test_strategy_catalog_consistency.py already asserts for every catalog entry.
    for entry in STRATEGY_CATALOG:
        strategy = build_strategy_from_dict(entry.name, {})
        assert strategy.name  # all strategies declare a `name` class var
        assert strategy.parameters  # all strategies expose parameters for the manifest


def test_build_strategy_returns_the_right_concrete_class() -> None:
    strategy = build_strategy(SMAConfig(fast=5, slow=20))
    assert isinstance(strategy, SMAStrategy)
    assert strategy.parameters == {"fast": 5, "slow": 20}


def test_build_strategy_from_dict_validates_through_pydantic() -> None:
    strategy = build_strategy_from_dict("sma", {"fast": 5, "slow": 20})
    assert isinstance(strategy, SMAStrategy)


def test_build_strategy_from_dict_rejects_unknown_name() -> None:
    with pytest.raises(ValidationError):
        build_strategy_from_dict("bogus", {"fast": 5})


def test_build_strategy_from_dict_rejects_invalid_pydantic_constraint() -> None:
    # RSIMeanReversionConfig requires 0 < oversold < 100; 150 fails Pydantic, not the
    # strategy constructor.
    with pytest.raises(ValidationError):
        build_strategy_from_dict(
            "rsi_mean_reversion", {"window": 14, "oversold": 150, "overbought": 70}
        )


def test_build_strategy_from_dict_surfaces_constructor_cross_param_rejection() -> None:
    # SMA's `fast < slow` lives in the strategy constructor (cross-parameter, can't be
    # expressed in a single Field constraint). Verify it propagates up cleanly.
    with pytest.raises(ValueError, match="fast"):
        build_strategy_from_dict("sma", {"fast": 50, "slow": 20})
