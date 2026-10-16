# FINDING-256: Exact holdout scores can lose strict predicate evidence in projection

- **Date:** 2026-10-16
- **Status:** Open — separate precision contract required
- **Area:** GraduationGate native comparisons versus GateResult float projection

An original HoldoutScore Sharpe Fraction(1,10**400) is strictly positive and above
benchmark0, while finite float inspection rounds it to0. With the valid manual
report/years12/trials100 from FINDING-255, native holdout predicates and passed
are True. GateResult publishes holdout_sharpe=0.0. Replaying the default strict
positive predicate on that projected scalar would fail. The current result
contract binds passed to its component vector, not to replaying scalar predicates.

This is not malformed original evidence: the exact-real source comparisons are
correct. No actual persisted market false graduate, corrupted normal production
output or changed calibration rate is established. The default engine returns
ordinary floats; the counterexample is a standalone accepted numeric source.

ADR-301 deliberately preserves native operands and this preexisting result while
closing invalid-source domains. Its finite float inspection cannot certify exact
output projection. A future correction needs an explicit precision contract and
ADR: reject lossy boundary projections, retain exact source representations or
change comparison arithmetic each have distinct compatibility consequences.
Do not silently switch native comparisons or thresholds in a scalar-validity fix.
No code or generated record is changed for this finding; no historical result is
reinterpreted. Preserve a regression control in the companion boundary tests.
