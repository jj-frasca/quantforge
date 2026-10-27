# ADR-387: Bind infinite required history to MinTRL rejection

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session8, ISO2026-W44
- **Resolves:** FINDING-329 within validated GateResult claims
- **Extends:** ADR-015/102/147/158/160/162/296/386

## Context

GateResult accepts an impossible passing MinTRL leg with positive-infinite required
history, including ordinary graduates, experiments, stores and counterfactual
calibration verdicts. ADR-296 requires finite available history, which cannot
satisfy infinity. Production evaluation already enforces that comparison; no
production false graduate or incompatible current generated leaf is established.
Independent research/data reviews confirm the narrow relationship and support
preserving all finite claims and legitimate infinite rejections.

## Options considered

1. **Refuse the contradictory relationship in the existing after-validator (chosen).**
   It binds the shared claim and reaches existing direct/nested instance validation
   and reconstructing outer/store boundaries without changing an evaluator.
2. **Rely on evaluation or only block graduates.** Rejected: stored rejected claims
   can still assert a false MinTRL component used in probability-DSR counterfactuals.
3. **Reject infinity, clip it, or repair the flag.** Rejected: changes the defined
   scientific result or silently replaces supplied evidence.
4. **Broaden instance/field revalidation globally.** Deferred: unnecessary for this
   after-validator relationship; other unchecked-field limitations are separate.

## Decision

After the existing conjunction mismatch refusal, reject exactly
required_track_record_years == math.inf and mintrl_ok with a ValueError naming
both fields. Keep holdout pairing and reasons freezing in their existing order.
Every finite requirement/mintrl flag combination, existing coercions, scalar
constraints, infinity/mintrlFalse, JSON Infinity tag and native Python output stay.
No estimator, duration comparison, threshold, config hash, search, accounting-v14,
calibration procedure or generated-data change. Existing finite claims cannot be
recomputed without available duration, which GateResult does not contain.

## Consequences, verification and reversal

Ordinary direct/JSON and existing nested validation refuse an internally impossible
leg, even when another component rejects. No historical repair or provenance claim.
After-validators rerun on supplied model instances; unchecked direct use without
validation and unrelated skipped field constraints remain outside the guarantee.

Tests first reproduce direct/mapping/JSON and actual outer/store acceptance, then
cover reconstructed unchecked instances, finite extremes, legitimate infinity,
Hypothesis relationship invariants and existing error precedence. Replay608 frozen
complete valid claims and the scoped AST; obtain independent final review and
foreground full gates before individual publication and exact CI verification.

Remove only the relationship guard to reverse; preserve the finding, which reopens.
