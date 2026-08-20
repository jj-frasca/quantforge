# ADR-057: Record WHICH strategy won each power cell, so a capture change can be attributed

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-056 (two-timescale reversion), ADR-045 (capture efficiency), ADR-053 (committed power record)
- **Relates to**: ADR-046 (candidate accounting), ADR-051 (measure at production parity)

## Context

ADR-056 added a strategy to the catalog and re-dispatched the calibration workflows to see whether
the band-reversion cells' net capture moves. That comparison — one power sweep before a catalog
change against one after — is the first *paired* reading this project has attempted, and it has a
confound the existing record cannot resolve.

`PowerCalibration.capture_ratio` is `median(finalist_observed_sharpes) / median(oracle_sharpes)`.
The numerator is the in-sample maximum over the searched grid. Adding a 35th strategy enlarges that
grid for **every** cell, and the maximum of more draws is larger in expectation *even when the added
strategy never wins anything*. So a capture rise after ADR-056 has two possible causes:

1. the new strategy expresses the planted process and becomes the finalist — ADR-056's hypothesis; or
2. the grid simply got bigger and selection noise moved the maximum — a pure artifact.

The artifact pushes in the same direction as the hypothesis, which is the worst case. Nothing in the
committed record distinguishes them: `finalist_observed_sharpes` carries the winning Sharpe of each
searched symbol but not the winner's identity, even though `_finalist(experiment)` already holds a
`Trial` whose `strategy_name` is right there.

This is the same failure mode ADR-052 repaired for the research pool (an experiment that cannot name
the search family that produced it), and ADR-049 repaired for the gate (a zero-power result that
cannot say which component refused). The instrument records an outcome without recording what
produced it.

## Decision

**Record the finalist's strategy name for every searched symbol in a power cell, and report the
distribution beside the capture ratio.**

1. `PowerCalibration.finalist_strategy_names: list[str]` — one entry per SEARCHED symbol, aligned
   index-for-index with `finalist_observed_sharpes`. Defaulted to `[]` so every committed artifact
   still loads and reports no attribution rather than a wrong one.
2. A `finalist_strategy_counts` computed field: name → count, empty when the list does not cover
   every searched symbol. Computed rather than stored for the ADR-055 reason — a dashboard or a
   script that re-derived it from the raw list could disagree with the served value.
3. `scripts/consolidate_power_calibration.py` prints the modal finalist and its share beside each
   cell's capture ratio, so the attribution is read at the same moment as the number it qualifies.

**The reading rule this creates, which is the point of the ADR:** a capture change between two
sweeps is attributable to a catalog change only if the finalist distribution moved toward the added
strategy. If capture rises while the finalist mix is unchanged, the rise is selection over a larger
grid and must be reported as such.

## Alternatives considered

- **Store the whole finalist `Trial` per symbol.** Rejected: it carries parameters, PBO, stability
  and both DSR statistics for 50 symbols × 12 cells, which is a large artifact for one question,
  and the pool is already the place where full trials live. The name is what the attribution needs.
- **Hold the grid size fixed across the comparison** (drop a strategy when adding one). Rejected —
  it would make the sweep measure a catalog the project does not run, violating ADR-051's parity
  principle, and the choice of which strategy to drop would itself bias the result.
- **Compute the expected selection inflation analytically and subtract it.** Rejected as a
  correction that would have to assume a correlation structure across the grid's configs. Recording
  the winner measures the thing directly instead of modelling it.
- **Do nothing and read capture deltas as-is.** Rejected. It is exactly the class of unattributable
  reading that ADR-055 had to retract twice (the 0%-power cells, and the "matched oracle" pairing).

## Amendment (2026-08-20, same session) — make the reading rule code, not prose

ADR-056's first paired reading landed while this ADR was being implemented, and it showed why the
rule above cannot live only in prose. The band cells moved by ≤ +0.7pp (noise) while **all four**
non-zero AR(1) detection cells moved down by 2–4pp — each inside binomial noise at n=50, but all in
the direction the ADR-046 accounting predicts when the catalog grows. A reader comparing two
committed sweeps by eye has to remember four separate qualifications to not over-read that.

**Decision 4: `compare_power_sweeps(before, after)` returns one row per matched cell** carrying the
capture deltas, the detection delta, and — the load-bearing part — an `attributable` flag that is
true only when **both** sides record finalist names AND the finalist mix actually moved. Cells that
exist on only one side are reported as unmatched rather than silently dropped, and a mismatch in
`edge`, `n_bars` or `gate_config_version` refuses the whole comparison the way `collect_power_sweep`
already refuses a mixed sweep. A DIFFERENT `search_config_version` across the two sides is
**required**, not refused: it is the catalog change being measured, and comparing two sweeps of the
identical search family is the one case where a capture delta is pure noise.

The rule the flag encodes: *a capture change is attributable to a catalog change only if the
finalist distribution moved toward the added strategy.* This is the same move `compare_with_null`
made for ADR-038/039's revisit trigger — a comparison the project kept getting wrong by hand became
a function with a refusal in it.

## Consequences

- The two power workflows must be re-dispatched for the attribution to exist; the sweeps dispatched
  under ADR-056 (runs 32423792873 / 32423795372) predate the field and will report no attribution.
  They remain valid for the capture number itself.
- Every future catalog change gets a cheap, honest answer to "did the new thing actually win?" —
  including the negative answer, which ADR-056 §Consequences already commits to reporting.
- The null calibration is deliberately NOT given this field: a null run has no planted process to
  capture, so a finalist's identity there is a fact about noise, not about expression.

## Reversal

Drop `finalist_strategy_names` and `finalist_strategy_counts` from `PowerCalibration`, the one line
in `calibrate_power` that appends to it, the modal-finalist column in the consolidation script, and
`compare_power_sweeps` with its `PowerSweepComparison` row.
No stored artifact is invalidated — the field is defaulted, and every capture number is computed
from lists this ADR does not touch.
