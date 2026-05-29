"""Parameter stability: identical Sharpes are maximally stable, erratic less so, fraction-profitable reflects signs; Hypothesis invariant that scores are bounded in [0,1]."""

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation.parameter_stability import parameter_stability


def test_identical_sharpes_are_maximally_stable() -> None:
    result = parameter_stability([1.5, 1.5, 1.5, 1.5])
    assert result.std_sharpe == pytest.approx(0.0)
    assert result.stability_score == pytest.approx(1.0)
    assert result.fraction_profitable == 1.0


def test_widely_varying_sharpes_are_less_stable() -> None:
    stable = parameter_stability([1.0, 1.1, 0.9, 1.0])
    erratic = parameter_stability([2.0, -1.0, 1.5, -0.5])
    assert erratic.stability_score < stable.stability_score


def test_fraction_profitable_reflects_signs() -> None:
    assert parameter_stability([1.0, 2.0, 0.5]).fraction_profitable == 1.0
    assert parameter_stability([-1.0, -2.0]).fraction_profitable == 0.0
    assert parameter_stability([1.0, -1.0]).fraction_profitable == pytest.approx(0.5)


def test_requires_at_least_two_configs() -> None:
    with pytest.raises(ValueError, match="config"):
        parameter_stability([1.0])


@given(
    sharpes=st.lists(
        st.floats(
            min_value=-10.0,
            max_value=10.0,
            allow_nan=False,
            allow_infinity=False,
            allow_subnormal=False,
        ),
        min_size=2,
        max_size=30,
    )
)
def test_scores_are_bounded(sharpes: list[float]) -> None:
    result = parameter_stability(sharpes)
    assert 0.0 <= result.stability_score <= 1.0
    assert 0.0 <= result.fraction_profitable <= 1.0
    # mean lies within [min, max] (tiny tolerance for float rounding)
    assert result.min_sharpe - 1e-9 <= result.mean_sharpe <= result.max_sharpe + 1e-9
