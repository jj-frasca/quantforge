# ADR-226: Bind the null graduate holdout maximum to its recorded graduates

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Resolves:** FINDING-176
- **Extends:** ADR-036, ADR-037, ADR-213, ADR-224

## Context

NullCalibration accepts a finite max_holdout_sharpe unrelated to its required
graduate list. With no graduates it accepts 10; with a graduate scoring 2 it
accepts None. Single-shard merge silently normalizes these false claims. The
native producer and merge define this field as the maximum among graduates,
not among all searched finalists. All eight committed artifacts are coherent.

## Decision

Require max_holdout_sharpe to equal the maximum holdout_sharpe in the graduate
list, with None exactly when that list is empty. Apply to modern and legacy
artifacts alike: the required graduate list already supplies the evidence.
Refuse contradictions before merge rather than overwriting the stored claim.

Preserve signed scores, graduate order, absent joints and nullable probabilities.
Do not infer trial-wide max_deflated_sharpe from selected graduate margins. Do
not bind the separately reported deflation_bar, change a threshold, estimator,
fingerprint, producer, source, JSON shape or generated record in this slice.

## Alternatives and limits

A modern-joint-only guard leaves the same false claim in legacy records whose
required graduate list is equally authoritative. A merge-only repair silently
conceals the contradiction and leaves standalone reporting unsafe. Taking the
maximum over all joint verdicts changes the established graduates-only meaning.

## Verification

Observe direct/JSON and unchecked reconstruction/merge failures before code.
Protect empty lists, negative and tied scores, graduate order, absent joints,
native production, all eight committed artifacts and unchanged trial-wide margin
meaning. Correct contradictory synthetic fixture summaries while preserving
original hostile inputs and rejection assertions. Run the full foreground gate.

## Reversal

Remove the root maximum relationship guard; contradictory reported maxima become
acceptable again without changing producer arithmetic.
