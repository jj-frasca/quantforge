# ADR-048: Enforce a fair, order-robust candidate budget

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-014/016 (search and `GateConfig`), ADR-044/046/047 (calibration identity,
  whole-search accounting, adaptive refinement)
- **Finding**: `docs/findings/FINDING-003-trial-budget-not-enforced.md`

## Context

`GateConfig.trial_budget=200` is versioned and persisted but no search path reads it. The default
34-family longitudinal catalog resolves 667 coarse configurations at `n_per_param=3`, then may add
an adaptive refined grid. Artifacts therefore advertise a budget while production can evaluate far
more hypotheses and consume unbounded compute.

Enforcement cannot be a list slice. Caller order would decide which families and parameter regions
exist, so two calls requesting the same set in a different order could select different finalists.
The budget must also leave at least two configurations in every searched family because PBO cannot
be computed from one configuration. Adaptive refinement needs capacity inside the same cap rather
than being appended after coarse search.

## Decision

**Enforce `trial_budget` as a hard per-search cap with canonical family ordering, fair family-level
allocation, deterministic space-filling selection, and an explicit adaptive-refinement reserve.**

1. Resolve known, eligible families, remove duplicates, and sort by canonical strategy name. Input
   order is not part of the selection procedure; cross-family ties therefore resolve canonically.
2. Treat each coarse family as one allocation bucket. When refinement is enabled, treat the one
   future winner-family refinement pass as one additional bucket.
3. Give every bucket two slots first. If the budget cannot supply two coarse configurations per
   family plus two refinement slots when requested, fail before any backtest. Do not silently drop a
   family or disable refinement.
4. Distribute remaining slots by water-filling the bucket with the smallest current allocation,
   stopping a coarse bucket at its full resolved-grid size. Stable bucket name breaks equal-allocation
   ties. The refinement bucket is capped by the winner-independent Cartesian maximum implied by
   `n_per_param` and the eligible families' parameter counts; its exact valid grid remains unknown
   until the coarse winner supplies a center.
5. When a full family grid exceeds its quota, choose a deterministic maximin subset in normalized
   parameter space: start nearest the grid center, then repeatedly add the point farthest from the
   selected set, with serialized parameters as the tie-break. This preserves broad parameter
   coverage without making Cartesian-product order scientifically meaningful.
6. After the coarse winner is known, generate its normal ADR-047 refined grid and apply the reserved
   quota with the same maximin rule. If fewer than two valid refined configs survive, skip refinement;
   unused capacity remains unused. The total evaluated candidates can never exceed `trial_budget`.
7. Apply the same coarse-family policy to cross-sectional search. It has no refinement bucket today.

Calibration identity hashes the canonical budgeted coarse grids, the refinement reserve, and a
budget-allocation method version. The existing `GateConfig` hash already carries the numeric budget.
Null and power artifacts produced before this ADR remain readable but are stale for production and
must be refreshed by their ADR-030 cloud sole writers. No generated `data/*.json` is edited locally.

No DSR, PBO, MinTRL, stability, holdout, beat-buy-and-hold, or universe-deflation threshold changes.
The smaller searched family changes the experiment being judged; it does not lower its bar.

## Alternatives considered

1. **Reject any requested grid larger than 200.** Honest but makes the default full-catalog hunt
   unusable and delegates the allocation decision inconsistently to every caller.
2. **Take the first 200 concrete configs.** Rejected: catalog or caller order chooses the hypotheses,
   later families disappear, and reordering changes results.
3. **Reduce `n_per_param` globally until the grid fits.** At two points per parameter the current
   coarse catalog still resolves 197 configs, leaving almost no adaptive reserve; families with more
   parameters also continue to consume exponentially more budget than simple families.
4. **Allocate proportional to full-grid size.** Rejected: it rewards parameter-rich families for
   having more knobs and recreates the multiplicity imbalance the cap is meant to control.
5. **Reserve a fixed percentage for refinement.** Rejected as arbitrary. Treating refinement as one
   additional family gives it the same marginal search budget as every coarse family and adapts as
   the catalog grows.
6. **Raise the default budget above 667.** Rejected: it would make the field technically active while
   preserving the compute and multiplicity problem that motivated the 200-candidate contract.

## Consequences

- Default production and calibration searches evaluate at most 200 concrete configurations,
  including adaptive refinement, and record that exact count for DSR and MinTRL.
- Every eligible requested family remains represented when the budget is feasible; high-dimensional
  families no longer dominate merely because their Cartesian grids are larger.
- Reordering or duplicating requested family names cannot change selected hypotheses or tie outcomes.
- Search results and calibration measurements will change. Null and power workflows must be rerun
  before current Type-I, power, and capture figures are described as production measurements.
- A very small custom budget now raises a precise pre-backtest error instead of producing an invalid
  one-config PBO family or silently searching a different family set.

## Reversal

Remove the allocation helper and restore full grids in both search paths, remove the allocation
method/reserve from calibration identity, and accept that `trial_budget` is again inert. This would
intentionally restore FINDING-003.
