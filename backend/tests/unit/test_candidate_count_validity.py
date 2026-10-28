"""ADR-396: generic candidate limits/capacities are original discrete counts."""

from decimal import Decimal
from fractions import Fraction
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.candidate_budget import (
    allocate_candidate_budget,
    select_space_filling_candidates,
)

INVALID = [
    None,
    True,
    False,
    np.bool_(True),
    np.bool_(False),
    0.0,
    2.0,
    1.5,
    np.float64(2.0),
    Fraction(2, 1),
    Decimal(2),
    "2",
    np.array(2),
    np.array([1, 2]),
    float("nan"),
    float("inf"),
    -float("inf"),
    -1,
    np.int64(-1),
    2 + 0j,
]


def _parameters(point: int) -> dict[str, int]:
    return {"value": point}


@pytest.mark.parametrize("bad", INVALID)
@pytest.mark.parametrize("size", [0, 1, 5])
def test_candidate_limit_refuses_original_invalid_count_before_shortcuts(
    bad: Any, size: int
) -> None:
    with pytest.raises(ValueError, match="limit must be a nonnegative nonboolean integer"):
        select_space_filling_candidates(tuple(range(size)), bad, parameters=_parameters)


@pytest.mark.parametrize("bad", INVALID)
@pytest.mark.parametrize("name", ["budget", "refinement_capacity"])
@pytest.mark.parametrize("size", [0, 1, 5])
def test_candidate_allocator_refuses_invalid_counts_before_eligibility(
    bad: Any, name: str, size: int
) -> None:
    families = {"a": tuple(range(size))} if size else {}
    settings = {"budget": 10, "refinement_capacity": 0}
    settings[name] = bad
    with pytest.raises(ValueError, match=rf"{name} must be a nonnegative nonboolean integer"):
        allocate_candidate_budget(families, parameters=_parameters, **settings)


class _Uninspectable:
    def __len__(self) -> int:
        raise AssertionError("candidate inspection before count validation")

    def items(self) -> object:
        raise AssertionError("family inspection before count validation")


@pytest.mark.parametrize("bad", [None, True, 1.5])
def test_candidate_limit_refuses_before_candidate_inspection_or_callback(bad: Any) -> None:
    with pytest.raises(ValueError, match="limit must be a nonnegative nonboolean integer"):
        select_space_filling_candidates(_Uninspectable(), bad, parameters=_parameters)


@pytest.mark.parametrize("name", ["budget", "refinement_capacity"])
@pytest.mark.parametrize("bad", [None, True, 2.5])
def test_candidate_allocator_refuses_before_family_inspection(name: str, bad: Any) -> None:
    settings = {"budget": 10, "refinement_capacity": 0}
    settings[name] = bad
    with pytest.raises(ValueError, match=rf"{name} must be a nonnegative nonboolean integer"):
        allocate_candidate_budget(_Uninspectable(), parameters=_parameters, **settings)


def test_candidate_budget_error_precedes_invalid_refinement_capacity() -> None:
    with pytest.raises(ValueError, match="budget must be a nonnegative nonboolean integer"):
        allocate_candidate_budget({}, budget=1.5, refinement_capacity=None, parameters=_parameters)


@pytest.mark.parametrize(
    "count", [0, 1, 2, 4, 100, 2**100, np.int8(127), np.int64(2**63 - 1), np.uint64(2**64 - 1)]
)
def test_candidate_valid_integral_limits_match_python_counts(count: int) -> None:
    points = tuple(range(5))
    result = select_space_filling_candidates(points, count, parameters=_parameters)
    assert result == select_space_filling_candidates(points, int(count), parameters=_parameters)
    assert len(result) == min(5, int(count))


@pytest.mark.parametrize(
    "count", [4, 8, 100, 2**100, np.int8(127), np.int64(2**63 - 1), np.uint64(2**64 - 1)]
)
def test_candidate_valid_integral_budgets_match_python_arithmetic(count: int) -> None:
    families = {"a": tuple(range(5))}
    result = allocate_candidate_budget(
        families, budget=count, refinement_capacity=5, parameters=_parameters
    )
    expected = allocate_candidate_budget(
        families, budget=int(count), refinement_capacity=5, parameters=_parameters
    )
    assert result == expected
    assert result.n_allocated <= int(count)
    assert type(result.refinement_reserve) is int


@pytest.mark.parametrize("capacity", [0, 1, 2, 5, np.int64(2**63 - 1), np.uint64(2**64 - 1)])
def test_candidate_valid_capacity_normalizes_before_arithmetic(capacity: int) -> None:
    families = {"a": tuple(range(5))}
    result = allocate_candidate_budget(
        families, budget=8, refinement_capacity=capacity, parameters=_parameters
    )
    assert result == allocate_candidate_budget(
        families, budget=8, refinement_capacity=int(capacity), parameters=_parameters
    )
    assert result.n_allocated <= 8


def test_candidate_zero_empty_and_refinement_only_rules_are_preserved() -> None:
    empty = allocate_candidate_budget({}, budget=0, parameters=_parameters)
    assert empty.families == {} and empty.n_allocated == 0
    ineligible = allocate_candidate_budget({"a": (1,)}, budget=0, parameters=_parameters)
    assert ineligible.n_allocated == 0
    reserve = allocate_candidate_budget({}, budget=4, refinement_capacity=5, parameters=_parameters)
    assert reserve.families == {} and reserve.refinement_reserve == reserve.n_allocated == 4
    assert select_space_filling_candidates((0, 1), 0, parameters=_parameters) == ()


@given(size=st.integers(0, 15), limit=st.integers(0, 20))
def test_candidate_integer_limit_is_an_actual_selection_cap(size: int, limit: int) -> None:
    selected = select_space_filling_candidates(tuple(range(size)), limit, parameters=_parameters)
    assert len(selected) == min(size, limit)
    assert len(selected) == len(set(selected))


@given(
    sizes=st.lists(st.integers(0, 8), min_size=0, max_size=4),
    budget=st.integers(0, 25),
    capacity=st.integers(0, 9),
)
def test_candidate_integer_budget_and_capacity_bound_every_allocation(
    sizes: list[int], budget: int, capacity: int
) -> None:
    families = {str(i): tuple(range(size)) for i, size in enumerate(sizes)}
    buckets = sum(size >= 2 for size in sizes) + int(capacity >= 2)
    if budget < 2 * buckets:
        with pytest.raises(ValueError, match="at least"):
            allocate_candidate_budget(
                families, budget=budget, refinement_capacity=capacity, parameters=_parameters
            )
        return
    result = allocate_candidate_budget(
        families, budget=budget, refinement_capacity=capacity, parameters=_parameters
    )
    assert result.n_allocated <= budget
    assert result.refinement_reserve <= capacity
    assert list(result.families) == sorted(result.families)
    for name, points in result.families.items():
        assert 2 <= len(points) <= len(families[name])
