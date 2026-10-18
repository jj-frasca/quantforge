"""ADR-317: stability measures one supported original real scalar per config."""

import warnings
from decimal import Decimal
from fractions import Fraction
from typing import cast

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.parameter_stability import parameter_stability


@pytest.mark.parametrize(
    "bad",
    [
        True,
        False,
        np.bool_(True),
        np.bool_(False),
        "1.5",
        b"1.5",
        1 + 0j,
        1 + 5j,
        None,
        Decimal("1.5"),
        object(),
        [1.5],
        (1.5,),
        np.array(1.5),
        {"score": 1.5},
        float("nan"),
        float("inf"),
        -float("inf"),
        np.float32("nan"),
        10**400,
    ],
)
def test_invalid_original_leaf_refuses_before_array_conversion(
    bad: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_conversion(*args: object, **kwargs: object) -> None:
        pytest.fail("invalid original evidence reached NumPy array conversion")

    monkeypatch.setattr(np, "asarray", forbidden_conversion)
    with pytest.raises(ValueError, match="finite real"):
        parameter_stability(cast(list[float], [1.5, bad]))


@pytest.mark.parametrize(
    "values",
    [
        np.array([True, True]),
        np.array(["1.5", "1.5"]),
        np.array([1 + 5j, 1 + 7j]),
        np.array([1 + 0j, 1 + 0j]),
        np.ones((2, 2)),
        [[1.5], [1.5]],
        np.empty((2, 0)),
    ],
)
def test_coercion_witnesses_refuse_without_conversion_warning(values: object) -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(ValueError, match="finite real"):
            parameter_stability(cast(list[float], values))
    assert not caught


def test_numeric_label_dataframe_refuses_matrix_before_reduction() -> None:
    values = pd.DataFrame([[1.0, 1.0], [1.0, 1.0]], columns=[1.0, 2.0])
    assert list(values) == [1.0, 2.0]
    with pytest.raises(ValueError, match="one-dimensional"):
        parameter_stability(cast(list[float], values))


@pytest.mark.parametrize("error", [TypeError, ValueError, OverflowError])
def test_real_scalar_inspection_failure_is_value_error(error: type[Exception]) -> None:
    class BrokenFloat(float):
        def __float__(self) -> float:
            raise error("uninspectable")

    with pytest.raises(ValueError, match="finite real"):
        parameter_stability([1.0, BrokenFloat(1.5)])


@pytest.mark.parametrize("values", [[], [True], [float("nan")], [[1.5]]])
def test_minimum_config_count_precedes_original_scalar_guard(values: list[object]) -> None:
    with pytest.raises(ValueError, match="need >= 2 configurations"):
        parameter_stability(cast(list[float], values))


@pytest.mark.parametrize(
    "values",
    [
        [1.5, 1.5],
        (1.5, 1.5),
        [Fraction(3, 2), Fraction(3, 2)],
        [np.float32(1.5), np.float64(1.5)],
        np.array([1.5, 1.5]),
        np.array([Fraction(3, 2), 1.5], dtype=object),
        np.array([1.5, 1.5], dtype=np.longdouble),
    ],
)
def test_supported_real_sequences_preserve_exact_identical_summary(values: object) -> None:
    summary = parameter_stability(cast(list[float], values))
    assert summary.mean_sharpe == summary.min_sharpe == summary.max_sharpe == 1.5
    assert summary.std_sharpe == 0.0
    assert summary.fraction_profitable == summary.stability_score == 1.0


def test_signed_zero_and_integer_evidence_remain_supported() -> None:
    summary = parameter_stability(cast(list[float], [np.int64(-1), -0.0, 1]))
    assert summary.mean_sharpe == 0.0
    assert summary.std_sharpe == 1.0
    assert summary.min_sharpe == -1.0
    assert summary.max_sharpe == 1.0
    assert summary.fraction_profitable == 1 / 3
    assert 0.0 < summary.stability_score < 1e-8


@given(
    scores=st.lists(st.floats(-10, 10, allow_nan=False, allow_infinity=False), min_size=2),
    boolean=st.booleans(),
    position=st.integers(min_value=0, max_value=100),
)
def test_boolean_cannot_become_one_numeric_configuration(
    scores: list[float], boolean: bool, position: int
) -> None:
    original = list(scores)
    index = position % len(scores)
    mixed: list[object] = list(scores)
    mixed[index] = boolean
    with pytest.raises(ValueError, match="finite real"):
        parameter_stability(cast(list[float], mixed))
    assert scores == original


@given(value=st.integers(-1000, 1000), count=st.integers(2, 30))
def test_identical_dyadic_real_configurations_have_exact_stability(value: int, count: int) -> None:
    score = Fraction(value, 8)
    summary = parameter_stability(cast(list[float], [score] * count))
    assert summary.mean_sharpe == float(score)
    assert summary.std_sharpe == 0.0
    assert summary.stability_score == 1.0
    assert summary.fraction_profitable == float(value > 0)
