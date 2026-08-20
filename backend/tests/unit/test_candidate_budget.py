from dataclasses import dataclass

import pytest

from app.research.lab.candidate_budget import (
    allocate_candidate_budget,
    allocate_catalog_candidate_budget,
)
from app.research.strategies.catalog import STRATEGY_CATALOG


@dataclass(frozen=True)
class _Point:
    value: int

    @property
    def parameters(self) -> dict[str, int]:
        return {"value": self.value}


def _values(allocation: object) -> dict[str, list[int]]:
    families = allocation.families  # type: ignore[attr-defined]
    return {name: [point.value for point in points] for name, points in families.items()}


def test_allocation_is_independent_of_requested_family_order_and_duplicates() -> None:
    alpha = [_Point(value) for value in range(9)]
    beta = [_Point(value) for value in range(20, 29)]

    first = allocate_candidate_budget(
        {"beta": beta, "alpha": alpha},
        budget=10,
        refinement_capacity=9,
        parameters=lambda point: point.parameters,
    )
    second = allocate_candidate_budget(
        {"alpha": alpha, "beta": beta},
        budget=10,
        refinement_capacity=9,
        parameters=lambda point: point.parameters,
    )

    assert _values(first) == _values(second)
    assert list(first.families) == ["alpha", "beta"]
    assert first.refinement_reserve == second.refinement_reserve
    assert first.n_allocated == 10


def test_allocation_covers_the_center_and_parameter_space_extremes() -> None:
    allocation = allocate_candidate_budget(
        {"alpha": [_Point(value) for value in range(9)]},
        budget=3,
        parameters=lambda point: point.parameters,
    )

    assert set(_values(allocation)["alpha"]) == {0, 4, 8}


def test_refinement_is_a_family_sized_bucket_inside_the_same_cap() -> None:
    allocation = allocate_candidate_budget(
        {
            "alpha": [_Point(value) for value in range(9)],
            "beta": [_Point(value) for value in range(20, 29)],
        },
        budget=12,
        refinement_capacity=9,
        parameters=lambda point: point.parameters,
    )

    assert [len(points) for points in allocation.families.values()] == [4, 4]
    assert allocation.refinement_reserve == 4
    assert allocation.n_allocated == 12


def test_budget_too_small_for_two_pbo_configs_per_bucket_fails_loudly() -> None:
    with pytest.raises(ValueError, match="at least 6"):
        allocate_candidate_budget(
            {"alpha": [_Point(0), _Point(1)], "beta": [_Point(2), _Point(3)]},
            budget=5,
            refinement_capacity=2,
            parameters=lambda point: point.parameters,
        )


def test_budget_is_a_cap_when_the_resolved_search_space_is_smaller() -> None:
    allocation = allocate_candidate_budget(
        {"alpha": [_Point(0), _Point(1)]},
        budget=100,
        refinement_capacity=3,
        parameters=lambda point: point.parameters,
    )

    assert len(allocation.families["alpha"]) == 2
    assert allocation.refinement_reserve == 3
    assert allocation.n_allocated == 5


def test_default_catalog_budget_represents_every_family_inside_200_candidates() -> None:
    allocation = allocate_catalog_candidate_budget(
        [entry.name for entry in reversed(STRATEGY_CATALOG)],
        n_per_param=3,
        budget=200,
        refine=True,
    )

    assert list(allocation.families) == sorted(entry.name for entry in STRATEGY_CATALOG)
    assert all(len(candidates) >= 2 for candidates in allocation.families.values())
    assert allocation.refinement_reserve >= 2
    assert allocation.n_allocated == 200
