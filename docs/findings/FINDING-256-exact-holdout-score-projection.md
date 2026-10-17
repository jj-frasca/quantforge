# FINDING-256: Exact holdout scores can lose strict predicate evidence in projection

- **Date:** 2026-10-16
- **Status:** Resolved by ADR-309 evaluator predicate-projection contract
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


## Governed predicate-projection contract (ADR-309)

ADR-309 adds a narrow evaluator consumption rule: retain every original native
predicate, then refuse if binary64 score projection changes the holdout or active
benchmark comparison verdict in either direction. The checked float Sharpe is
the published snapshot. Coherent but inexact projections remain accepted, so
Fraction(1,3) does not require exact float representation. No tolerance, changed
strict inequality, threshold or default is introduced.

The reverse mismatch also exists. With NumPy float32(0.1) and configured Python
threshold 0.1, the native comparison is False, while the projected Python float
0.10000000149011612 exceeds that threshold. Substituting float predicates would
change the native decision. The new guard instead refuses an incoherent claim,
even if another component already fails. A disabled benchmark stays inactive;
its source is still validated, but its ordering need not survive projection.

This explicitly narrows originally valid numeric-source acceptance; it does not
retroactively label those exact/native comparisons malformed. The earlier
reproduction above remains a record of the pre-ADR-309 behavior. No actual
production corruption, market false graduate or changed calibration rate is
established. Ordinary production float scores retain their original predicates.

GateResult does not store the benchmark score or the actual configured floor.
This rule ensures evaluator-issued predicate compatibility with the projected
scores while the original inputs/config are available; GateResult alone still
cannot replay the benchmark or establish provenance. Original total-return
wealth comparison and exact integer bar-count normalization remain unchanged.
In particular an original return greater than -1 that rounds to -1 still has
its ADR-301 acceptance; downstream Graduate wealth representability is separate.
This is not a complete holdout serialization-coherence claim.

Actual pre-production RED closed with 15 failed and 132 preserved cases
(`/tmp/qf-w42-s28-projection-red.log`): initial 35 new cases plus 112 existing,
including the intentionally changed F256 witness. The final focused run passed
253 cases, including 38 new; three benchmark-specific cases were added after
the first green run, not claimed as pre-code RED. Ruff, formatting and mypy
passed. The original witness still asserts its exact-versus-projected arithmetic
and source identity, but now requires the governed refusal.

Parent independent source/test review approved the narrow four-statement guard
and checked-float publication. AST comparison preserves every original predicate,
reason and all other module code exactly; the rest of the existing companion
test file remains byte-identical. All 288 pre-change ordinary GateResult payloads
match exactly, SHA256
`69fa25ab666cc692c7f06192cf7cb8ad374cb40b96abab71dfe1ddd15233401f`.
Receipts: `/tmp/qf-w42-s28-projection-source-audit.json` and
`/tmp/qf-w42-s28-gate-projection-baseline.json`; independent arithmetic witness
`/tmp/qf-w42-s28-projection-parent-probe.json`. These are hand-built unit
mechanics, not source cohorts or power measurements.

Fresh full foreground `make check-all` passed 12,598 backend tests (97.40%
coverage) and 401 frontend tests (97.68% statements), with lint, formatting and
strict types green. All local verification is closed. The evaluator predicate
projection gap is resolved; exact master CI is checked after publishing. No generated records,
frozen cohorts, source draws, search arithmetic, v14 identity or thresholds change.
