# ADR-275: Compute integer beta from exact covariance sufficient sums

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 6, ISO 2026-W42
- **Resolves:** FINDING-224
- **Extends:** ADR-269, ADR-270

## Context

Distinct integer neighbors near int64max compared to themselves publish beta zero
and annual alpha about 2.324e21 instead of beta one and alpha zero. Native pandas
moment calculations erase source distinctions; float64 arrays used by scaled
recovery also see a fabricated constant. Both-unsigned and mixed excess fixes do
not correct these source moments. All four plain/masked 64-bit families reproduce.

## Options considered

1. Exact Python integer sufficient sums for supported both-integer sources, with
   one final integer-ratio division to float. Bounded source widths make this cheap.
2. Translate exact integers, certify native encoding, then reuse wider moments.
   Initially supported by 768 scratch oracles, but rejected before this decision:
   it unnecessarily declines some 53-bit encodings and can leave nonzero native
   residuals for exact zero covariance. Exact sums close both limitations.
3. Rewrite every source moment. Unnecessary noninteger compatibility change.
4. Use Fraction objects in production or a value-size trigger. Neither is needed:
   sufficient integer sums remain exact with O(1) additional memory.

## Decision

After existing source validation/alignment and exact constant detection, dispatch
only when both original sources have native integer dtype kind i/u or classic
masked Int/UInt8/16/32/64. Either exact constant still yields beta zero before
integer moments. Noninteger, mixed integer/float and native wider paths retain
all existing code and estimators; no observation-size trigger is added.

For each original source subtract its own first observation as Python integers.
Streaming accumulation retains sum(ds), sum(db), sum(ds*db) and sum(db*db).
For n aligned rows, compute the exact integers
num=n*sum(ds*db)-sum(ds)*sum(db) and den=n*sum(db*db)-sum(db)**2.
Require den>0, then divide num/den directly as Python integers to final float beta.
The sample n-1 and n factors cancel in this same covariance/variance definition.
No intermediate float conversion, native moment/encoding, scaled fallback or
production Fraction objects are needed. Accumulator bit growth is bounded by
roughly 128+2log2(n) for these at-most-64-bit source observations.

All integer pairs deliberately receive this estimator path, so their beta rounding
may change even when old moments were adequate. Original means/alpha formula stay
(alpha naturally changes with corrected beta); excess, IR/TE, drawdown, metadata,
source guards and error state remain. Final finite-statistic validation remains.
No threshold, calibration identity, workflow, schema or generated record changes.

## Evidence and limits

Independent exact-sum prototype agrees with 540 centered Fraction oracles across
n=2,3,4,7,16,128, full uint64 range, huge origins, neighbors and uneven cancellation.
A 100,000-row scratch probe took about 0.046 seconds. Native wider translated
moments incorrectly return beta about 4.07e-20 for a constructed exact-zero
covariance; integer sums give zero. Require genuine public RED before code,
independent Fraction/Hypothesis invariants, constant/guard precedence, alignment,
ownership/state and complete outside-path preservation. Run independent final
review, foreground make check-all and exact master CI before delivery.

This certifies integer covariance sufficient sums, not original source means,
alpha aggregation, excess or other statistic precision. Final beta is a float;
other scalar limitations remain, and historical contamination is not established.
There is no universal whole-comparator precision or strict-state guarantee.

## Reversal

Remove the both-integer beta predicate/dispatch and exact sum helper. This reopens
FINDING-224 while retaining the separate exact excess and native wider fixes.
