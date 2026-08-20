"""Deterministic candidate-budget allocation for research searches (ADR-048)."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from app.research.strategies.base import BaseStrategy
from app.research.strategies.grid_generator import find_catalog_entry, grid_from_catalog

ParameterMap = Mapping[str, float | int]

_MIN_CONFIGS_FOR_PBO = 2
_REFINEMENT_BUCKET = "~adaptive_refinement"


def _numeric_strategy_parameters(strategy: BaseStrategy) -> dict[str, float | int]:
    return {
        name: value for name, value in strategy.parameters.items() if isinstance(value, int | float)
    }


@dataclass(frozen=True)
class CandidateBudget[CandidateT]:
    """Concrete family grids plus capacity reserved for one adaptive refinement pass."""

    families: dict[str, tuple[CandidateT, ...]]
    refinement_reserve: int = 0

    @property
    def n_allocated(self) -> int:
        return sum(len(candidates) for candidates in self.families.values()) + (
            self.refinement_reserve
        )


def _parameter_key(parameters: ParameterMap) -> tuple[tuple[str, float], ...]:
    return tuple((name, float(value)) for name, value in sorted(parameters.items()))


def select_space_filling_candidates[CandidateT](
    candidates: Sequence[CandidateT],
    limit: int,
    *,
    parameters: Callable[[CandidateT], ParameterMap],
) -> tuple[CandidateT, ...]:
    """Choose a stable maximin subset in normalized parameter space.

    The first point is nearest the grid center. Each later point maximizes its minimum distance
    from the selected set, so a quota covers the resolved parameter region rather than inheriting
    arbitrary Cartesian-product ordering. Serialized parameters break every tie deterministically.
    """
    if limit < 0:
        raise ValueError("candidate limit must be >= 0")
    if limit >= len(candidates):
        return tuple(candidates)
    if limit == 0:
        return ()

    parameter_maps = [parameters(candidate) for candidate in candidates]
    keys = sorted({key for point in parameter_maps for key in point})
    vectors: list[tuple[float, ...]] = []
    for key in keys:
        if any(key not in point for point in parameter_maps):
            raise ValueError("all candidates in a family must expose the same parameters")
    for point in parameter_maps:
        vectors.append(tuple(float(point[key]) for key in keys))

    minima = tuple(min(vector[i] for vector in vectors) for i in range(len(keys)))
    maxima = tuple(max(vector[i] for vector in vectors) for i in range(len(keys)))
    normalized = [
        tuple(
            0.5 if maxima[i] == minima[i] else (value - minima[i]) / (maxima[i] - minima[i])
            for i, value in enumerate(vector)
        )
        for vector in vectors
    ]
    canonical = [_parameter_key(point) for point in parameter_maps]

    def distance_squared(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        return sum((a - b) ** 2 for a, b in zip(left, right, strict=True))

    center = tuple(0.5 for _ in keys)
    first = min(
        range(len(candidates)),
        key=lambda index: (distance_squared(normalized[index], center), canonical[index]),
    )
    selected = [first]
    remaining = set(range(len(candidates))) - {first}
    while len(selected) < limit:
        next_index = min(
            remaining,
            key=lambda index: (
                -min(
                    distance_squared(normalized[index], normalized[chosen]) for chosen in selected
                ),
                canonical[index],
            ),
        )
        selected.append(next_index)
        remaining.remove(next_index)
    return tuple(candidates[index] for index in selected)


def allocate_candidate_budget[CandidateT](
    families: Mapping[str, Sequence[CandidateT]],
    *,
    budget: int,
    parameters: Callable[[CandidateT], ParameterMap],
    refinement_capacity: int = 0,
) -> CandidateBudget[CandidateT]:
    """Allocate a hard cap fairly across canonical family buckets (ADR-048).

    Families with fewer than two candidates are ineligible for PBO and are omitted. Every eligible
    coarse family, plus refinement when its possible capacity is at least two, receives two slots
    before remaining capacity is water-filled. An impossible minimum fails before any backtest.
    """
    eligible = {
        name: tuple(candidates)
        for name, candidates in sorted(families.items())
        if len(candidates) >= _MIN_CONFIGS_FOR_PBO
    }
    capacities = {name: len(candidates) for name, candidates in eligible.items()}
    if refinement_capacity >= _MIN_CONFIGS_FOR_PBO:
        capacities[_REFINEMENT_BUCKET] = refinement_capacity
    if not capacities:
        return CandidateBudget(families={})

    minimum_required = _MIN_CONFIGS_FOR_PBO * len(capacities)
    if budget < minimum_required:
        raise ValueError(
            f"trial_budget must be at least {minimum_required} to allocate "
            f"{_MIN_CONFIGS_FOR_PBO} PBO configs to each requested search bucket"
        )

    quotas = dict.fromkeys(capacities, _MIN_CONFIGS_FOR_PBO)
    remaining = budget - minimum_required
    while remaining:
        unsaturated = [name for name in capacities if quotas[name] < capacities[name]]
        if not unsaturated:
            break
        bucket = min(unsaturated, key=lambda name: (quotas[name], name))
        quotas[bucket] += 1
        remaining -= 1

    selected = {
        name: select_space_filling_candidates(eligible[name], quotas[name], parameters=parameters)
        for name in eligible
    }
    return CandidateBudget(
        families=selected,
        refinement_reserve=quotas.get(_REFINEMENT_BUCKET, 0),
    )


def allocate_catalog_candidate_budget(
    strategy_names: Sequence[str],
    *,
    n_per_param: int,
    budget: int,
    refine: bool,
) -> CandidateBudget[BaseStrategy]:
    """Resolve and budget the longitudinal catalog exactly as production search does."""
    entries = {
        name: entry
        for name in sorted(set(strategy_names))
        if (entry := find_catalog_entry(name)) is not None
    }
    grids = {
        name: grid_from_catalog(entry, n_per_param=n_per_param) for name, entry in entries.items()
    }
    eligible_entries = {
        name: entry for name, entry in entries.items() if len(grids[name]) >= _MIN_CONFIGS_FOR_PBO
    }
    refinement_capacity = (
        max(
            (n_per_param ** len(entry.parameters) for entry in eligible_entries.values()), default=0
        )
        if refine
        else 0
    )
    return allocate_candidate_budget(
        grids,
        budget=budget,
        refinement_capacity=refinement_capacity,
        parameters=_numeric_strategy_parameters,
    )
