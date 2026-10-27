# FINDING-329: Infinite required history can claim MinTRL passage

- **Status:** Corrected within validated GateResult claims under ADR-387
- **Date:** 2026-10-27
- **Producing revision:** e59a1545
- **Affected:** GateResult and validated nested graduate/experiment/calibration claims

## Evidence

An ordinary GateResult accepts required_track_record_years=positive infinity,
mintrl_ok=True and all six components/passed=True. A CalibrationSymbolVerdict
with probability 0.99 then reports counterfactual composite passage. A Graduate
with matching finite holdout evidence, a complete Experiment, and both JSON pool
writers also accept the claim. Independent data/research object-only witnesses
and the parent receipt reproduce this without running a search or provider.

ADR-296 requires finite available track-record history; no finite duration can
satisfy an infinite requirement. ADR-015/160 intentionally retain that requirement
for nonpositive observed Sharpe. The missing relationship is therefore an internal
claim contradiction, not evidence that ordinary production evaluation graduates
such candidates. The same contradiction is accepted when dsr_ok=False and
passed=False; an overall rejection does not make its MinTRL leg coherent.

After safe sync, a read-only audit of 617 research/null/power JSON files validates
3,969 complete gate leaves, all with finite requirements and zero prospective
incompatibilities. All file hashes remain unchanged. No affected historical row,
production graduate, trade, calibration rate or source provenance is established.

## Correction and limits

ADR-387 adds only the relationship refusal in GateResult's existing after-validator:
positive-infinite requirement with mintrl_ok=True raises ValueError. It applies
regardless of overall passage. Finite requirements and legitimate infinite
requirements with mintrl_ok=False retain their existing values/representation.
Conjunction validation keeps its existing precedence; no finite duration cap,
MinTRL formula, threshold, evaluator, hash, accounting-v14 or generated data changes.

The existing after-validator reruns for GateResult instances supplied directly or
nested in CalibrationSymbolVerdict. Outer graduate, experiment, calibration and
store boundaries also reconstruct claims. Tests must check these actual paths.
Reviewers initially inferred an instance bypass from skipped field validation;
a separate conjunction-invalid-copy witness disproved that inference before
adoption. Skipped field constraints on deliberately unchecked copies remain a
separate limitation. Direct use of a copy without validation is not certified.
The guard cannot verify finite requirement/pass claims against absent available
history, reconstruct lost historical evidence, or establish market-data truth.

## Verification

Written finding, independent prospective reviews and ADR precede tests/source.
A frozen baseline captures 608 complete valid JSON/Python claims spanning all
component vectors, finite extremes/signed zero and legitimate infinite rejection,
plus the gate AST outside the exact proposed guard. All 29 actual pre-code
failures are missing ValidationError, with two controls passing; no harness/import
failures are included. The 31 new tests then pass. The parent 158, research 78 and
data 169 focused synthetic tests pass. Both independent final reviewers approve;
parent and reviewers replay 608 complete valid claims and the scoped AST exactly.
Data also verifies refusal leaves existing store bytes unchanged.

The tests cover constructor/mapping/JSON/instance validation, legacy holdout pairs,
failed overall conjunctions, four complete artifact roots, supplied nested instances,
both actual store writers, Hypothesis finite preservation and infinite rejection,
and existing conjunction-error precedence. Full foreground gate and exact post-push
CI receipts are recorded in the session ledger. No generated data is edited.
