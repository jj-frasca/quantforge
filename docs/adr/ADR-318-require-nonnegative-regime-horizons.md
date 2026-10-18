# ADR-318: Require original nonnegative regime horizons

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 33, ISO 2026-W42
- **Extends:** ADR-012/295
- **Resolves:** FINDING-269

## Context

analyze_regimes describes its labels as the sign of a trailing market return.
Its public window parameter is passed unchecked to pandas pct_change. Negative
periods use future prices: a market change at t+1 can switch the regime attached
to an otherwise unchanged strategy return at t. Two independent handbuilt
witnesses demonstrate this for -1 and -2 horizons. Current ValidationEngine
uses the default20, containing the defect on that route. No affected production
report, calibration or false graduate is established.

## Decision

Before alignment or market access, validate window through the existing
require_trial_count(window, minimum=0, parameter="window") helper. Original
nonboolean Integral scalars must be nonnegative and normalize to Python int.
Reject floats, fractions, strings, complex values, missing values, arrays and
both boolean families rather than coerce them or clamp negative horizons.

Preserve zero as the existing degenerate all-bull horizon on finite positive
market prices. It cannot read future prices and is not a trend measurement.
Preserve default20 and every current alignment, pct_change, warmup-bull,
grouping, compounding and Sharpe operation. The only runtime changes are the
shared helper import and one guard/normalization assignment. No helper change,
report schema, threshold, gate/search identity or accounting-v14 change.

This guard does not certify market calendar ordering, source completeness,
missing/nonpositive prices, alignment policy, arbitrary huge pandas horizons
or native arithmetic. Regime metrics remain retrospective descriptive
partitions, not a self-financing account or an executable regime-switching
strategy. Source-order and other evidence boundaries are separate decisions.

## Options considered

1. Reuse the shared original-integral guard before data work.
   Chosen: explicit original evidence and mathematical Python count semantics.
2. Apply abs/int/round to arbitrary horizons.
   Rejected: silently changes the caller's horizon and erases invalid evidence.
3. Remove the public window parameter or require strictly positive horizons.
   Rejected: broader compatibility change; zero is already supported and has
   no future dependence under the stated valid-source control.
4. Rely on the fixed default caller.
   Rejected: a public helper still promises a trailing partition.

## Verification and reversal

Observe RED before code: negative horizons, original invalid scalar classes,
refusal before align/pct_change even for empty input, and fixed-width count
normalization. Preserve zero/default/positive/NumPy-integral controls and test
prefix/future-perturbation label membership with Hypothesis on bounded ordered
positive sources. Compare original timestamp memberships, not whole-report
aggregates which legitimately include later observations. Twenty valid result
payloads are frozen for exact comparison; entire original AST must survive
after removing only the import, one guard and docstring change.

Independent review, foreground make check-all and exact CI are mandatory.
Removing the assignment/import reopens negative-horizon future labeling; retain
this decision and the original written witness if reversing.
