# ADR-246: Require unique paired capture cell keys

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-195
- **Extends:** ADR-057, ADR-103
- **Relates to:** ADR-158, ADR-241, ADR-245

## Context

ADR-103/FINDING-035 already establish that file ordering must not choose a
comparison's evidence and refuse duplicate strong-edge cells in the probability
comparator. The separate ADR-057 capture comparator still builds key dictionaries
without a uniqueness refusal. Duplicate effect cells silently select the last
record; reversing two before cells changes an attributable delta from -0.5 to
+0.5. This is remaining consumer coverage of the existing identity principle,
not a novel mathematical flaw or changed production result.

## Options Considered

1. Refuse duplicate existing effective comparison keys on either side before
   constructing dictionaries. Preserves valid identity and reading semantics.
2. Pick the first/last record or deduplicate. Lets ordering select evidence.
3. Pool cells or invent a new key. Changes the reported process or comparison
   identity rather than refusing an ambiguous existing record.

## Decision

At compare_power_sweeps, retain existing edge/history/gate/search refusals first,
then require unique effective keys within each side before dictionary creation.
Use precisely the existing phi-if-present, otherwise half_life-or-zero key.
Raise ValueError for collisions, including equal signed-zero and legacy fallback
keys. Identical records duplicated at a key are still ambiguous and refused.

Do not change producer collection, direct PowerSweep schema, optional process
parameter domains, key representation, matched/unmatched reporting or attribution.
Nested wrapper/cell identity binding is a separate boundary. No observation is
pooled, selected or deleted; no threshold, estimator, source or artifact changes.

## Verification and reversal

Observe before/after duplicate keys and both input orders failing before code.
Verify band, AR, signed-zero and missing-parameter collisions, valid exact public
rows, sorted union/unmatched behavior and identity-refusal precedence. Use
Hypothesis for unique input-order invariance. Independent review and full
foreground verification precede delivery. Removing the guard reopens FINDING-195.
