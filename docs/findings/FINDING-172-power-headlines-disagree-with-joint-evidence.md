# FINDING-172: Power headlines disagree with canonical joint evidence

- **Date:** 2026-10-08
- **Severity:** High — contradictory modern calibration claims
- **Status:** Resolved by ADR-222
- **Reproduced revision:** `92835a65`

PowerCalibration accepts internally coherent scalar counts/rates that contradict
its complete symbol_verdicts: zero detections despite incumbent passers, zero
survivors despite passed records above their own ADR-018 bars, and component
counts below or otherwise different from their canonical sums. These records
can report one power/bottleneck while their canonical observations say another.

Independent review reproduced three contradictory typed roots with 50 joint
records, ten incumbent passers and measured holdout score 5 over one year. The
ordinary producer uses the same incumbent result and per-record holdout for
all these quantities. All 12 committed power cells lack joint records; their
legacy measurements remain valid and unmeasured for these relationships.

This is a synthetic evidence-boundary defect, not an observed corrupt committed
artifact, a changed gate result or qualifying candidate comparison. ADR-222
conditionally binds modern detection, per-record strict survival and present
known component counts to the complete joint evidence. None candidate
probabilities, absent legacy records, empty/partial component mappings and
unknown keys remain supported. No displayed-bar identity, null-side policy,
threshold, estimator, fingerprint, source, workflow or data change.

## Correction and verification

The pre-code baseline had 21 failing contradiction cases and ten preserved
cases. All 88 focused reconciliation/probability/joint cases pass. Independent
final review approved the slice and ran 91 cases including three native
producer cases; all 12 committed legacy cells round-trip unchanged. Coverage
includes strict own-record bar boundaries, mixed histories, incumbent
nonpassers, nullable candidates, partial/unknown mappings, JSON and unchecked
root/nested changes. No incoherent affected fixture was observed. Full
foreground delivery verification is recorded in the session state.
