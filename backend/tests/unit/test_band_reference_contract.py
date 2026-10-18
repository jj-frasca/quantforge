"""ADR313 nominal-law metadata, sign scores and preflight contracts."""

from fractions import Fraction
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab import calibration as c


def reference(**updates: Any) -> Any:
    return c.BandReference.model_validate(
        {
            "method": "band_conditional_simple_mean_sign_zero_start_v1",
            "drift": 0.0003,
            "total_vol": 0.012,
            "start_price": 100.0,
        }
        | updates
    )


def test_band_reference_law_given_known_metadata_retains_nominal_parameters() -> None:
    law = c.band_reference_law(reference(), half_life=3.0, deviation_share=0.409)
    assert law.rho == 0.5 ** (1.0 / 3.0)
    assert law.deviation_vol == 0.012 * np.sqrt(0.409 / (2.0 * (1.0 - law.rho)))
    assert law.half_life == 3.0
    assert law.deviation_share == 0.409


@pytest.mark.parametrize(
    "updates", [{"drift": True}, {"total_vol": 0}, {"start_price": "100"}, {"extra": 1}]
)
def test_band_reference_given_invalid_metadata_refuses(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        reference(**updates)


@given(
    st.floats(allow_nan=False, allow_infinity=False),
    st.floats(min_value=5e-324, allow_nan=False, allow_infinity=False),
)
def test_band_reference_score_given_binary64_matches_fraction_sign(
    m: float, variance: float
) -> None:
    score_fn = c.band_reference_sign_score
    doubled = 2.0 * m
    score = doubled + variance
    if not np.isfinite(doubled) or not np.isfinite(score):
        with pytest.raises(ValueError):
            score_fn(m, variance)
    else:
        exact = 2 * Fraction(m) + Fraction(variance)
        assert np.sign(score_fn(m, variance)) == ((exact > 0) - (exact < 0))


def test_band_reference_preflight_given_invalid_later_symbol_calls_nothing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(c, "oracle_sharpe_of", lambda *a, **k: calls.append("score"))
    monkeypatch.setattr(c, "run_search", lambda *a, **k: calls.append("search"))
    index = pd.date_range("2020-01-01", periods=3)
    frames = {
        "a": pd.DataFrame({"close": [100.0, 101.0, 102.0]}, index=index),
        "b": pd.DataFrame({"close": [100.0, 0.0, 102.0]}, index=index),
    }
    deviations = {key: pd.Series([0.0, 0.0, 0.0], index=index) for key in frames}
    with pytest.raises(ValueError):
        c.measure_power(
            frames,
            [],
            band_reference=reference(),
            band_deviations=deviations,
            edge="band_reversion",
            half_life=3.0,
            deviation_share=0.409,
        )
    assert calls == []


def cell(**updates: Any) -> c.PowerCalibration:
    return c.PowerCalibration.model_validate(
        {
            "n_symbols": 1,
            "n_detected": 0,
            "detection_rate": 0.0,
            "n_clear_deflation_bar": 0,
            "deflation_bar": 0.0,
            "oracle_sharpes": [],
            "holdout_years": [],
            "errors": {},
            "edge": "band_reversion",
            "half_life": 3.0,
            "deviation_share": 0.409,
            "band_reference": reference(),
            "n_bars": [1000],
            "gate_config_version": "g",
            "search_config_version": "s",
            **updates,
        }
    )


@pytest.mark.parametrize(
    "updates",
    [
        {"phi": 0.2},
        {"edge": "ar1"},
        {"half_life": True},
        {"deviation_share": Fraction(2**55 - 1, 2**55)},
        {"deviation_share": Fraction(2**55 + 1, 2**55)},
        {"half_life": 1e300},
        {"deviation_share": 0.0},
    ],
)
def test_band_reference_cell_given_invalid_coordinates_refuses(updates: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        cell(**updates)


def test_band_reference_collect_given_unchecked_copy_or_mixed_identity_refuses() -> None:
    original = cell()
    for bad in [
        original.model_copy(update={"phi": 0.2}),
        cell(band_reference=None),
        cell(band_reference=reference(drift=0.01)),
    ]:
        with pytest.raises(ValueError):
            c.collect_power_sweep([original, bad])
    with pytest.raises(ValueError):
        c.collect_power_sweep([original]).model_validate(
            c.collect_power_sweep([original]).model_dump() | {"band_reference": None}
        )


def test_band_reference_compare_given_share_mismatch_refuses_before_ratios() -> None:
    before = c.collect_power_sweep([cell()])
    after = c.collect_power_sweep([cell(deviation_share=0.5, search_config_version="new")])
    with pytest.raises(ValueError, match="deviation_share"):
        c.compare_power_sweeps(before, after)
    unmatched = c.collect_power_sweep(
        [cell(half_life=5.0, deviation_share=0.5, search_config_version="new")]
    )
    assert all(row.net_capture_delta is None for row in c.compare_power_sweeps(before, unmatched))


@pytest.mark.parametrize("share", [0.409, 1.0])
def test_band_reference_predictions_given_hand_prices_match_joint_gaussian(share: float) -> None:
    from app.research.lab.band_reference import band_reference_preflight

    ref = reference(start_price=0.5, drift=-0.001)
    law = c.band_reference_law(ref, half_life=3.0, deviation_share=share)
    index = pd.date_range("2020-01-01", periods=4)
    prices = np.array([0.501, 0.498, 0.502, 0.499])
    states = np.array([0.001, -0.002, 0.003, 0.001])
    frame = pd.DataFrame({"close": prices}, index=index)
    owned, predictions = band_reference_preflight(
        {"X": frame}, {"X": pd.Series(states, index=index)}, ref, law
    )
    latent, observed = predictions["X"]
    assert np.isnan(latent.iloc[0]) and np.isnan(observed.iloc[0])
    q = law.deviation_vol**2 * (1 - law.rho**2)
    noise = law.level_vol**2
    delta = law.rho - 1
    for i in range(1, 4):
        # Independent finite joint covariance of levels and AR deviations.
        covariance = np.array(
            [
                [
                    q * sum(law.rho ** (a + b - 2 * k) for k in range(min(a, b) + 1))
                    for b in range(i)
                ]
                for a in range(i)
            ]
        )
        level_covariance = np.array([[noise * (min(a, b) + 1) for b in range(i)] for a in range(i)])
        y = np.log(prices[:i]) - np.log(ref.start_price) - np.arange(1, i + 1) * ref.drift
        cross = covariance[i - 1]
        mean = cross @ np.linalg.solve(covariance + level_covariance, y)
        variance = covariance[i - 1, i - 1] - cross @ np.linalg.solve(
            covariance + level_covariance, cross
        )
        expected = 2 * (ref.drift + delta * mean) + q + noise + delta**2 * variance
        assert observed.iloc[i] == pytest.approx(expected, abs=1e-14)
        assert latent.iloc[i] == 2 * (ref.drift + delta * states[i - 1]) + (q + noise)
    frame.iloc[0, 0] = 9.0
    assert owned["X"].iloc[0, 0] == prices[0]


@pytest.mark.parametrize(
    "bad",
    [
        pd.Series([True] * 3),
        pd.Series([1.0, np.nan, 2.0]),
        pd.Series([1 + 1j] * 3),
        pd.Series(["0"] * 3),
    ],
)
def test_band_reference_source_given_invalid_deviation_calls_nothing(
    monkeypatch: pytest.MonkeyPatch, bad: pd.Series
) -> None:
    from unittest.mock import Mock

    score = Mock(side_effect=AssertionError("no scoring"))
    monkeypatch.setattr(c, "oracle_sharpe_of", score)
    monkeypatch.setattr(c, "run_search", score)
    with pytest.raises(ValueError):
        c.measure_power(
            {"X": pd.DataFrame({"close": [1.0, 2.0, 3.0]})},
            [],
            band_reference=reference(),
            band_deviations={"X": bad},
            edge="band_reversion",
            half_life=3.0,
            deviation_share=0.409,
        )
    score.assert_not_called()


def test_band_reference_preflight_given_categorical_axis_owns_categories() -> None:
    from app.research.lab.band_reference import band_reference_preflight

    frame = pd.DataFrame(
        {"close": [1.0, 2.0, 3.0]},
        index=pd.CategoricalIndex([1, 2, 3], categories=[1, 2, 3], ordered=True),
    )
    ref = reference()
    owned, predictions = band_reference_preflight(
        {"X": frame},
        {"X": pd.Series([0.0, 0.0, 0.0], index=frame.index)},
        ref,
        c.band_reference_law(ref, half_life=3.0, deviation_share=0.409),
    )
    categories = frame.index.categories.to_numpy()
    categories.flags.writeable = True
    categories[0] = 9
    assert list(owned["X"].index) == [1, 2, 3]
    assert list(predictions["X"][0].index) == [1, 2, 3]


def test_band_reference_preflight_given_duplicate_columns_refuses_value_error() -> None:
    from app.research.lab.band_reference import band_reference_preflight

    ref = reference()
    with pytest.raises(ValueError):
        band_reference_preflight(
            {"X": pd.DataFrame([[1.0, 1.0], [2.0, 2.0]], columns=["close", "close"])},
            {"X": pd.Series([0.0, 0.0])},
            ref,
            c.band_reference_law(ref, half_life=3.0, deviation_share=0.409),
        )


def test_band_reference_dispatch_given_valid_sources_preserves_costs_and_owned_frames(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from unittest.mock import Mock

    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=pd.Index([1, 2, 3]))
    deviation = pd.Series([0.1, 0.2, 0.3], index=frame.index)
    captures: list[tuple[pd.DataFrame, pd.Series, float]] = []

    def scorer(owned: pd.DataFrame, predicted: pd.Series, *, cost_rate: float = 0.0) -> float:
        captures.append((owned, predicted.copy(), cost_rate))
        frame.iloc[0, 0] = 9.0
        deviation.iloc[0] = 9.0
        index_owner = frame.index.to_numpy()
        index_owner.flags.writeable = True
        index_owner[0] = 9
        assert list(owned.index) == [1, 2, 3]
        assert list(predicted.index) == [1, 2, 3]
        return 1.0

    search = Mock(side_effect=ValueError("mock unsearchable"))
    monkeypatch.setattr(c, "oracle_sharpe_of", scorer)
    monkeypatch.setattr(c, "run_search", search)
    with pytest.raises(ValueError, match="can be searched"):
        c.measure_power(
            {"X": frame},
            [],
            band_reference=reference(),
            band_deviations={"X": deviation},
            edge="band_reversion",
            half_life=3.0,
            deviation_share=0.409,
        )
    assert [item[2] for item in captures] == [0.0, c.DEFAULT_COST_RATE, c.DEFAULT_COST_RATE]
    assert all(item[0] is captures[0][0] for item in captures)
    assert search.call_args.args[0] is captures[0][0]
    assert captures[0][0].iloc[0, 0] == 1.0
    assert np.isnan(captures[0][1].iloc[0])


@pytest.mark.parametrize(
    "updates",
    [
        {"phi": 0.2},
        {"ar1_reference": {"method": "ar1_phi_lag_sign_v1", "drift": None}},
        {"oracle_sharpes": {}},
        {"net_oracle_sharpes": {}},
        {"achievable_oracle_sharpes": {}},
        {"edge": "ar1"},
        {"band_deviations": {}},
    ],
)
def test_band_reference_dispatch_given_contradictions_calls_nothing(
    monkeypatch: pytest.MonkeyPatch, updates: dict[str, Any]
) -> None:
    from unittest.mock import Mock

    mock = Mock(side_effect=AssertionError("no scoring/search"))
    monkeypatch.setattr(c, "oracle_sharpe_of", mock)
    monkeypatch.setattr(c, "run_search", mock)
    kwargs = {
        "band_reference": reference(),
        "band_deviations": {"X": pd.Series([0.0, 0.0])},
        "edge": "band_reversion",
        "half_life": 3.0,
        "deviation_share": 0.409,
    } | updates
    with pytest.raises(ValueError):
        c.measure_power({"X": pd.DataFrame({"close": [1.0, 2.0]})}, [], **kwargs)
    mock.assert_not_called()


def test_band_reference_metadata_given_scalar_conversion_type_error_refuses_value_error() -> None:
    class Broken(float):
        def __float__(self) -> float:
            raise TypeError("broken scalar conversion")

    with pytest.raises(ValueError):
        reference(drift=Broken(0.1))


def test_band_reference_preflight_given_numpy_policy_preserves_policy() -> None:
    from app.research.lab.band_reference import band_reference_preflight

    ref = reference()
    before = np.geterr()
    try:
        np.seterr(all="raise")
        policy = np.geterr()
        frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
        band_reference_preflight(
            {"X": frame},
            {"X": pd.Series([0.0, 0.0, 0.0])},
            ref,
            c.band_reference_law(ref, half_life=3.0, deviation_share=1.0),
        )
        assert np.geterr() == policy
    finally:
        np.seterr(**before)


@pytest.mark.parametrize(
    "updates,h,share",
    [
        ({}, 1e300, 0.409),
        ({"total_vol": 1e-200}, 3.0, 0.409),
        ({"total_vol": 1e200}, 3.0, 0.409),
        ({}, 1e-320, 0.409),
        ({}, 3.0, Fraction(2**55 - 1, 2**55)),
    ],
)
def test_band_reference_law_given_unmeasurable_noise_refuses(
    updates: dict[str, Any], h: float, share: Any
) -> None:
    with pytest.raises(ValueError):
        c.band_reference_law(reference(**updates), half_life=h, deviation_share=share)


@pytest.mark.parametrize(
    "m,v",
    [
        (0.0, 5e-324),
        (-5e-324, 1e-323),
        (-0.0, 5e-324),
        (1e308, 1.0),
        (-1e308, 1.0),
        (0.0, 0.0),
        (float("nan"), 1.0),
        (0.0, float("inf")),
    ],
)
def test_band_reference_score_given_boundaries_preserves_sign_or_refuses(
    m: float, v: float
) -> None:
    if (
        not np.isfinite(m)
        or not np.isfinite(v)
        or v <= 0
        or not np.isfinite(2 * m)
        or not np.isfinite(2 * m + v)
    ):
        with pytest.raises(ValueError):
            c.band_reference_sign_score(m, v)
    else:
        exact = 2 * Fraction(m) + Fraction(v)
        assert np.sign(c.band_reference_sign_score(m, v)) == ((exact > 0) - (exact < 0))


def test_band_reference_sweep_given_unchecked_valid_dict_retains_validated_identity() -> None:
    known = cell()
    sweep = c.collect_power_sweep([known])
    unchecked = known.model_copy(update={"band_reference": reference().model_dump()})
    rebuilt = c.PowerSweep.model_validate(sweep.model_dump() | {"cells": [unchecked]})
    assert isinstance(rebuilt.cells[0].band_reference, c.BandReference)


@pytest.mark.parametrize(
    "kind", ["index", "duplicate-index", "returns", "original-overflow", "uncertainty"]
)
def test_band_reference_preflight_given_invalid_derived_source_refuses(
    kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.research.lab import band_reference as b

    ref = reference()
    law = c.band_reference_law(ref, half_life=3.0, deviation_share=0.409)
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
    states = pd.Series([0.0, 0.0, 0.0])
    if kind == "index":
        states.index = [1, 2, 3]
    elif kind == "duplicate-index":
        frame.index = states.index = [1, 1, 2]
    elif kind == "returns":
        frame["close"] = [5e-324, 1e308, 1.0]
    elif kind == "original-overflow":
        frame["close"] = np.array([1.0, np.finfo(np.longdouble).max, 3.0], dtype=np.longdouble)
    else:
        from app.research.lab.band_posterior import BandPricePosterior

        monkeypatch.setattr(
            b,
            "band_price_posterior",
            lambda *args, **kwargs: BandPricePosterior(np.zeros(3), np.full(3, 5e-324)),
        )
    with pytest.raises(ValueError):
        b.band_reference_preflight({"X": frame}, {"X": states}, ref, law)


def test_band_reference_predictions_given_zero_noise_consistent_states_are_causal() -> None:
    from app.research.lab.band_reference import band_reference_preflight

    ref = reference()
    law = c.band_reference_law(ref, half_life=3.0, deviation_share=1.0)
    deviations = pd.Series([0.001, -0.002, 0.004, -0.001])
    closes = ref.start_price * np.exp(np.arange(1, 5) * ref.drift + deviations.to_numpy())
    frame = pd.DataFrame({"close": closes})
    _, full = band_reference_preflight({"X": frame}, {"X": deviations}, ref, law)
    _, prefix = band_reference_preflight(
        {"X": frame.iloc[:3]}, {"X": deviations.iloc[:3]}, ref, law
    )
    np.testing.assert_allclose(full["X"][0], full["X"][1], atol=1e-15, rtol=1e-12, equal_nan=True)
    for whole, partial in zip(full["X"], prefix["X"], strict=True):
        np.testing.assert_array_equal(whole.iloc[:3], partial)


def test_band_reference_source_given_masked_deviation_refuses() -> None:
    from app.research.lab.band_reference import band_reference_preflight

    ref = reference()
    deviation = pd.Series(np.ma.array([0.0, 0.0, 0.0], mask=[False, True, False]))
    with pytest.raises(ValueError):
        band_reference_preflight(
            {"X": pd.DataFrame({"close": [1.0, 2.0, 3.0]})},
            {"X": deviation},
            ref,
            c.band_reference_law(ref, half_life=3.0, deviation_share=0.409),
        )
