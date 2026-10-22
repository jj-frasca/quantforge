# ADR-345: Refuse unmeasurable final universe annotation bars

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Codex autonomous session 17, ISO 2026-W43; independent research review
- **Resolves:** FINDING-295
- **Extends:** ADR-018/344

## Context

ADR-344 refuses original nonfinite supplied history, deliberately leaving
finite-derived arithmetic separate. At N607, finite native longdouble history
1e400 returns a zero bar, while Python history 2**-1074 returns infinity.
Independent Decimal100/160/240 exact-native-ratio model calculations give
positive representable answers around3.58009183990006e-200 and1.6106524564257913e162.
This establishes direct-helper result defects, not production incidence or
changed graduation/calibration rates. Ordinary producers derive durations
from validated finite bar counts.

## Options considered

1. Bind the unchanged final product and require finite positive evidence in
   the existing active branch. Small, explicit refusal; does not recover answers.
2. Replace reciprocal/square-root arithmetic with scaled or high-precision
   calculation. Could recover these answers but requires a separate accuracy,
   original-scalar and compatibility contract; defer.
3. Inspect or normalize all intermediate/input types. Broader than the finding;
   could reject currently supported native-wide controls or change warnings.
4. Retain zero/infinite derived annotations. Leaves undefined or lost evidence
   presented as a measured bar; reject.

## Decision

Keep ADR-344's original-history guard and the original N<2/T<=0 shortcut first.
In the remaining branch, retain the exact native reciprocal/sqrt/log operands,
bind the existing final product, and raise ValueError if that final Python float
is nonfinite or nonpositive. Return every accepted positive finite result
unchanged. No recovery, coercion, catches, warning filters or NumPy-policy changes.

Intentional finite nonpositive-history and no-selection shortcut zeros remain.
Native finite2*float64max history still gives1.8880843389847055e-154.
Some native tiny NumPy durations warn before the new refusal; under a caller's
raise policy their original FloatingPointError precedes the guard. Preserve
those native outcomes rather than promising universal ValueError.

This is not original N validation. Active NaN/infinite N values that formerly
produced NaN/infinite bars also refuse at the final result boundary; no-selection
inputs such as1.5, bool and negative infinity retain their original shortcut.
Other native input/operation exceptions propagate unchanged. A positive finite
result is not certification of all rounding accuracy, arbitrary custom types,
source provenance, Gaussian assumptions or selection independence.

Keep the annotation formula/model, thresholds, schemas, search/gate fingerprints
and accounting-v14 identity. Source provenance changes; no unchanged-rate claim
follows. Never replay, repair or relabel frozen/generated evidence.

## Verification

Write repository tests and observe meaningful RED before runtime edits.
Cover tiny Python/native durations and finite native-wide lost results, active
nonfinite N side effects, shortcut zeros, ordinary/wide controls, and native
warning/raise propagation. Financial Hypothesis properties use independent
Decimal exact-input model evidence for representable lost results.
Compare the complete prior module AST except the declared final binding/check/
return/docstring and compare unchanged positive/native outcomes. Preserve all
original tests. Require independent final review, foreground make check-all,
explicit-path individual publication and exact master CI.

## Reversal

Remove only the final-result binding/check and restore the prior return.
This reopens zero/infinite derived annotations while retaining ADR-344's
original-history refusal. Numerical recovery requires its own decision.
