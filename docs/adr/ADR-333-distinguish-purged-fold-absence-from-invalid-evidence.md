# ADR-333: Distinguish purged-fold absence from invalid evidence

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 8, ISO 2026-W43
- **Resolves:** FINDING-280
- **Extends:** ADR-039/078/198/199/202

## Context

ValidationEngine catches every purged evaluator ValueError as absent geometry.
A real causal synthetic strategy with tiny initial exposure has two usable
10-row training/60-row test folds, but unmeasurable native train dispersion.
The evaluator refuses; the engine publishes a null PCV plus a false insufficient-
history explanation. No passing report, production occurrence or graduate is
established by this witness. Structural refusals are equally ambiguous at this
catch boundary.

## Options Considered

1. Give genuine no-fold absence its own ValueError subtype at the evaluator's
   existing final check, and catch only it. Preserves full validation and error
   precedence, but adds a public semantic exception class.
2. Preflight generated fold sizes in the engine. Fewer source edits, but duplicates
   the evaluator's absence inference and skips its empty-fold validation path.
3. Keep catching everything and change only the flag. Avoids refusal-domain
   changes, but still allows invalid evidence to become an absent diagnostic.

## Decision

Add NoUsablePurgedFoldsError(ValueError) in purged_cv.py. Raise it only at the
existing final 'if not folds' check, retaining the exact message. All original
matrix/control/mask/embargo/geometry checks and empty-fold dropping run first.
No other refusal becomes this subtype. In ValidationEngine catch only that
subtype; keep genuine absence's null/count0/flag and all evaluator call arguments.
Other ValueErrors propagate with their original meaning. Correct the engine's
stale 'PCV only counted' docstring to describe the existing measured diagnostic.

## Consequences and limits

Direct callers catching ValueError retain compatibility for genuine absence;
callers inspecting its exact concrete type now see the new subtype. Invalid
evidence cannot masquerade as insufficient geometry. Successful numeric estimates,
true no-fold outputs, defaults, selection, thresholds and v14 estimator identity
remain. No numerical recovery, extra fold dropping or source validation bypass
is introduced.

This changes completion/refusal behavior for affected inputs. Longitudinal search
uses ValidationEngine; calibration may now record such a refusal as an error and
exclude it from its completed denominator. Do not infer unchanged rates from
unchanged finite formulas. No new calibration, historical cohort replay, artifact
rewrite or rate claim is authorized. Ordinary regression controls are bounded
evidence, not a guarantee against all numerical failures. The causal custom
probe establishes an error path, not a production occurrence or gate flip.

## Verification and reversal

Observe actual-engine numerical-refusal RED before implementation. Test semantic
no-fold typing, retained ordinary ValueError compatibility, malformed all-empty
sources/rows/embargo refusal before absence, and propagation of unrelated evaluator
errors. Preserve 12 frozen complete ordinary/genuine-no-fold reports and all old
module AST except the new class, final raise type, engine import/catch/docstring.
Require independent review, foreground make check-all and individual push/exact
CI. Reverse the raise/catch/class to reopen FINDING-280; never relabel prior data.
