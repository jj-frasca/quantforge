# ADR-251: Bind direct forward scoring to target symbol

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-200
- **Extends:** ADR-139, ADR-148

## Context

The managed paper loop checks that its quality-gated dataset names the target
position's symbol. Direct evaluate_forward calls omit that relationship and can
return another symbol's performance, including through the zero-forward shortcut.
The later complete position boundary refuses mismatched evidence, but a direct
score consumer can use the result before attachment.

## Options Considered

1. Apply the existing manager symbol check at direct scorer entry.
   - Pro: closes the public boundary before copying prices or producing a score.
   - Con: repeats one existing relationship check inside managed scoring.
2. Rely exclusively on the manager and later position attachment.
   - Pro: no scorer change.
   - Con: direct score results still describe the wrong target.
3. Revalidate the complete position and every source field here.
   - Pro: could enforce broader position contracts.
   - Con: expands this identity correction into unrelated lifecycle/source policy.

## Decision

At evaluate_forward entry require dataset.quality_report.symbol to equal
position.symbol.strip().upper(), using the manager's existing comparison and
ValueError wording. Refuse before dataset.frame access, strategy construction
and both zero/nonzero-forward score paths. Keep the original scorer body and
evidence construction unchanged. Preserve normalized target equivalence and all
native output arithmetic, warmup, freeze geometry and caller objects.

## Consequences and reversal

Direct and managed forward scoring enforce the same target identity. Valid calls
pay one string comparison; mismatched calls now fail before producing performance
for another asset. Managed provider failures keep their existing fail-soft behavior.
No quality check, schema, estimator, threshold, lifecycle, broker or generated data
changes. Standalone frame-based lifecycle evaluation remains a separate consumer.
Remove the entry comparison to reverse this correction and reopen FINDING-200.
