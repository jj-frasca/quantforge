# FINDING-169: Power arrays accept invalid evidence

- **Date:** 2026-10-08
- **Severity:** High — durable power evidence validity
- **Status:** Resolved by ADR-219
- **Reproduced revision:** `29b70228`

PowerCalibration construction accepts NaN gross reference scores, boolean net
reference scores, string achievable scores, infinite finalist/category scores,
boolean bar counts, zero holdout years and boolean finalist probabilities.
Frozen containers preserve the malformed/coerced evidence; sweep reconstruction
cannot reject contracts missing from the authoritative model. Summary-access
checks alone do not establish durable artifact or capture-input validity.

These are malformed synthetic boundary inputs, not an observed corrupted
committed artifact or wrong gate verdict. ADR-219 validates original present
array elements with established score/history/probability contracts before
coercion, without filtering observations or inventing defaults. None remains
valid for nullable probabilities; empty/partial legacy arrays retain their
existing measurement and capture-refusal semantics.

No new length, process parameter, category key, component-count, strategy-name
or standalone joint-verdict contract is included. No threshold, reference,
fingerprint, sample or generated artifact changes are proposed. Frozen AR
replays continue on their loaded `29b70228` procedure and retain that attribution.

## Correction and verification

Sixty-four rejection cases failed before implementation, with 18 compatibility
cases already passing. All 159 focused array/root/comparison/endpoint cases
pass after reusing the established element guards. Read-only compatibility
covers all 12 committed cells: 2,100 reference/finalist scores, 2,400 category
scores, 600 bar counts and 600 year values; historical probability arrays are
empty. Present nullable/probability endpoint and exact pre-rounding bounds are
covered synthetically. Independent final review approved all five paths, ran
141 relevant tests, round-tripped all 12 committed cells unchanged and checked
matching nullable versus mismatched joint projections. No generated record or
threshold changes. Full foreground delivery verification is recorded in the
session state.
