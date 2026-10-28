# FINDING-333: Fractional direct candidate counts can overspend their caps

- **Status:** Confirmed on malformed direct calls; ADR-396 adopts original-count guards
- **Date:** 2026-10-28
- **Producing revision:** 72e0a849
- **Affected:** select_space_filling_candidates and allocate_candidate_budget

## Evidence and limits

On five integer points, the direct maximin selector with limit1.5 returns two
points. The generic allocator with one five-point family and budget2.5 allocates
all five. Its remaining budget0.5 crosses below zero but remains truthy, so the
water-filling loop continues until capacity saturates. Empty/ineligible inputs
can instead conceal malformed count inputs behind early returns. Type annotations
declare int but do not enforce the original runtime count domain.

An acquisition-free reproduction is:

```python
from app.research.lab.candidate_budget import (
    allocate_candidate_budget,
    select_space_filling_candidates,
)

points = tuple(range(5))
params = lambda x: {"x": x}
assert len(select_space_filling_candidates(points, 1.5, parameters=params)) == 2
assert allocate_candidate_budget({"a": points}, budget=2.5, parameters=params).n_allocated == 5
```

This describes the pre-396 implementation and deliberately supplies values
outside its annotated discrete domain. Parent and independent research reproduce
both results. Current ordinary production budgets arrive through validated
GateConfig fields; no production overrun, affected research count/graduate or
changed calibration rate is established. No search, provider or cohort is run.

## Correction and remaining scope

ADR-396 validates original nonnegative nonboolean Integral limit, budget and
refinement_capacity with the existing count helper, normalizing them to Python
integers before generic inspection, shortcuts or arithmetic. Budget validates
before capacity. Zero remains valid; minimum-two eligibility, canonical ordering,
maximin distance arithmetic, water filling and reserves retain their rules.

The catalog wrapper may construct grids before delegating to the generic
allocator. This correction does not establish early refusal before that grid
work, validate n_per_param or certify parameter-vector geometry. Large integer
counts gain no new cap. Existing negative-limit refusal remains tested under the
shared validator's more specific nonnegative-integer diagnostic.

The pre-source baseline freezes395 complete accepted-count selection/allocation/
error claims, five gate/search fingerprints and the whole module source. Actual
pre-code verification has190 failures and25 passing controls; all tests collect,
and failures exercise missing/wrong count refusals, diagnostics or premature
inspection. After the three entry checks,215 new tests pass; parent and
independent research each pass333 focused synthetic tests including existing
budget and SMA regressions. Both replay all395 claims/five fingerprints and the
whole AST outside the declared guards, negative-check replacement and import
unchanged. Final research review approves the six-path correction. Full foreground
gate and exact pushed CI receipts are recorded separately in the session ledger.
No threshold, method version, v14 or generated/frozen evidence changes.
