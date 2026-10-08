# FINDING-164: Synthetic power is not a certified market upper bound

- **Date:** 2026-10-08
- **Severity:** Medium — interpretation exceeds measured evidence
- **Status:** Resolved in active reporting
- **Reproduced revision:** `e5c9ca4f`

The dashboard says every synthetic detection rate is an upper bound on power
against real intermittent edges. `PowerCalibration` repeats that claim, inherited
from ADR-041. The table also labels its selected in-sample reference ratio
`Capture (upper bound)` despite the qualified reference contracts in FINDING-155
and FINDING-159.

Stationarity and constant parameter values do not establish an ordering of
detection probabilities between this source law and unspecified real-market
alternatives. Effect strength, signal horizon, catalog expressibility, costs,
history and sampling law can all differ. No matched coupling or stochastic
dominance argument is supplied. Calling these plants favorable controls is
reasonable; calling their measured rates universal market upper bounds is not
supported. This is an unsupported inference finding, not a measured market
counterexample or evidence that any real edge exists.

Likewise, selection can inflate an in-sample finalist/reference ratio, but
optimistic selection does not certify a bound on a future score or on the
fraction of an optimal edge captured. Its denominator is a stated historical
reference strategy, not a certified cost-aware or sample optimum.

The correction should label the ratio as in-sample and state that the synthetic
rates do not bound real-market power. Preserve all measured rates, ratios,
scores, counts, JSON fields and threshold values. Qualify active UI/docs while
leaving historical accepted ADRs and artifacts unchanged. This does not change
the validity of the fixed-cohort counts in FINDING-162/163 or authorize any
gate relaxation.

## Correction and verification

The panel labels capture as in-sample and qualifies synthetic power without a
real-market bound. The backend docstring and active cold-memory power/capture
claims receive the same correction. Historical ADRs and measured artifacts
remain intact. Independent research review approved the reasoning and scope;
backend executable AST is identical after stripping docstrings.

The associated FINDING-159 band-label correction observed three RED cases and
sixteen preserved cases before its patch. This upper-bound correction observed
two additional RED cases and nineteen preserved cases before its patch. Final
21 focused frontend cases, targeted lint and typecheck passed. Full foreground
`make check-all PYTEST_WORKERS=4` passed 3,318 backend and 363 frontend tests,
at 97.56% backend coverage and 97.63% frontend statements. All served scores,
ratios, detections and null displays are preserved. FINDING-159's mathematical
reference correction remains Open.
