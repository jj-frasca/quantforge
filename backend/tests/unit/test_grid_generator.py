"""Catalog-driven config grids: every catalog entry yields enough valid configs for
PBO; cross-parameter constraints (SMA fast<slow, RSI oversold<overbought) are filtered
out silently rather than crashing the grid build."""

import pytest

from app.research.strategies.catalog import (
    STRATEGY_CATALOG,
    ParamSchema,
    StrategySchema,
)
from app.research.strategies.grid_generator import (
    _refined_values,
    _values_for_param,
    find_catalog_entry,
    grid_from_catalog,
    refine_grid,
)
from app.research.strategies.sma import SMAStrategy


def test_find_catalog_entry_returns_match() -> None:
    entry = find_catalog_entry("sma")
    assert entry is not None
    assert entry.name == "sma"


def test_find_catalog_entry_returns_none_for_unknown_name() -> None:
    assert find_catalog_entry("bogus") is None


def test_values_for_param_uses_bounded_range() -> None:
    param = ParamSchema(name="fast", type="int", default=20, minimum=1, maximum=10, label="Fast")
    values = _values_for_param(param, n=3)
    assert min(values) >= 1
    assert max(values) <= 10
    assert all(isinstance(v, int) for v in values)


def test_values_for_param_falls_back_when_bounds_missing() -> None:
    # No minimum/maximum: fall back to default * [0.5, 1.5]
    param = ParamSchema(name="k", type="float", default=2.0, label="k")
    values = _values_for_param(param, n=3)
    assert min(values) >= 1.0
    assert max(values) <= 3.0


def test_values_for_param_single_value_is_just_the_default() -> None:
    param = ParamSchema(name="fast", type="int", default=20, label="Fast")
    assert _values_for_param(param, n=1) == [20]


def test_values_for_param_rejects_zero_n() -> None:
    param = ParamSchema(name="fast", type="int", default=20, label="Fast")
    with pytest.raises(ValueError, match="n_per_param"):
        _values_for_param(param, n=0)


def test_values_for_param_int_dedupe_on_collapsing_round() -> None:
    # Tight integer range where round() collapses neighboring linspace points to the
    # same integer. The set+sorted() should leave only the unique values.
    param = ParamSchema(name="x", type="int", default=1, minimum=1, maximum=2, label="x")
    values = _values_for_param(param, n=5)
    assert values == [1, 2]


def test_grid_from_catalog_yields_only_valid_strategies() -> None:
    # Every grid produces at least 2 valid configs (the PBO minimum). Cross-parameter
    # constraint violators are silently dropped — the grid is what survives.
    for entry in STRATEGY_CATALOG:
        configs = grid_from_catalog(entry, n_per_param=3)
        assert len(configs) >= 2, (
            f"{entry.name} grid produced too few valid configs for PBO; "
            f"either widen the catalog bounds or raise n_per_param"
        )


def test_grid_from_catalog_skips_cross_param_violations() -> None:
    # SMA's fast/slow grid would include combinations where fast >= slow if we didn't
    # filter — those should NOT appear in the returned strategies.
    sma_entry = find_catalog_entry("sma")
    assert sma_entry is not None
    configs = grid_from_catalog(sma_entry, n_per_param=4)
    for strategy in configs:
        assert isinstance(strategy, SMAStrategy)
        assert strategy.fast < strategy.slow


def test_grid_from_catalog_with_n_per_param_one_is_just_defaults() -> None:
    sma_entry = find_catalog_entry("sma")
    assert sma_entry is not None
    configs = grid_from_catalog(sma_entry, n_per_param=1)
    assert len(configs) == 1
    assert configs[0].parameters == {"fast": 20, "slow": 50}


def test_refine_grid_zooms_around_the_center_within_bounds() -> None:
    # Refine around fast=20/slow=50: values cluster near the center and stay valid (fast<slow).
    sma_entry = find_catalog_entry("sma")
    assert sma_entry is not None
    configs = refine_grid(sma_entry, {"fast": 20, "slow": 50}, n_per_param=3, span_frac=0.25)
    assert len(configs) >= 2
    for strategy in configs:
        assert isinstance(strategy, SMAStrategy)
        assert strategy.fast < strategy.slow
        assert 15 <= strategy.fast <= 25  # within +/-25% of 20
        assert 37 <= strategy.slow <= 63  # within +/-25% of 50


def test_refined_values_rejects_zero_n() -> None:
    param = ParamSchema(name="k", type="float", default=2.0, label="k")
    with pytest.raises(ValueError, match="n_per_param"):
        _refined_values(param, center=2.0, n=0, span_frac=0.25)


def test_refined_values_single_value_is_the_center() -> None:
    param = ParamSchema(name="fast", type="int", default=20, label="Fast")
    assert _refined_values(param, center=20.4, n=1, span_frac=0.25) == [20]


def test_refined_values_float_param_returns_floats() -> None:
    param = ParamSchema(name="k", type="float", default=2.0, label="k")
    values = _refined_values(param, center=2.0, n=3, span_frac=0.25)
    assert all(isinstance(v, float) for v in values)
    assert min(values) >= 1.5 and max(values) <= 2.5


def test_refined_values_degenerate_window_falls_back_to_center() -> None:
    # minimum clamps low ABOVE high -> degenerate window -> just the center value.
    param = ParamSchema(name="x", type="int", default=10, minimum=100, maximum=200, label="x")
    assert _refined_values(param, center=10.0, n=3, span_frac=0.25) == [10]


def test_refine_grid_filters_cross_param_violations() -> None:
    # Center fast=45/slow=50 with a wide-ish span produces some fast>=slow combos -> skipped.
    sma_entry = find_catalog_entry("sma")
    assert sma_entry is not None
    configs = refine_grid(sma_entry, {"fast": 45, "slow": 50}, n_per_param=3, span_frac=0.25)
    assert all(isinstance(s, SMAStrategy) and s.fast < s.slow for s in configs)


def test_refine_grid_missing_center_param_falls_back_to_default() -> None:
    sma_entry = find_catalog_entry("sma")
    assert sma_entry is not None
    # center omits 'slow' -> uses the catalog default (50) as the center for that param.
    configs = refine_grid(sma_entry, {"fast": 20}, n_per_param=3)
    assert len(configs) >= 2


def test_grid_from_catalog_handles_a_schema_with_no_params() -> None:
    # Defensive: a catalog entry could in principle have an empty parameter list
    # (zero-knob strategy). itertools.product() of an empty sequence yields one empty
    # tuple, which means we build a single default-args strategy.
    empty_entry = StrategySchema(
        name="sma",
        label="SMA",
        category="Trend",
        summary="",
        description="",
        citations=[],
        parameters=[],
    )
    configs = grid_from_catalog(empty_entry, n_per_param=3)
    assert len(configs) == 1
