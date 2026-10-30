# ADR-404: Preflight latest distress profitability operands

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session19, ISO2026-W44
- **Resolves:** FINDING-339 within latest-year financial_distress input consumption
- **Extends:** ADR-029/384/385; distinct from Piotroski's ADR-389

## Context

The direct distress consumer compares latest net income and operating cash flow
with zero without validating finiteness. NaN can erase invalidity into False;
negative infinity can contribute to True. Both ordinary histories and their
provider wrappers reproduce the issue, independently reviewed. Existing safety
guards cover different fields, and this consumer never calls Piotroski scoring.
No actual vendor incidence, graduate or trading effect is established.

## Options considered

1. **Validate the two consumed operands locally (chosen).**
   - Pro: refuses invalid boolean evidence while preserving unrelated consumers.
   - Con: reduces availability even when a missing peer or healthy balance sheet
     would previously have produced False.
2. **Make every AnnualFundamentals field finite globally.**
   - Pro: could protect all consumers at one boundary.
   - Con: changes provider/valuation availability, ignored rows and unrelated
     fields beyond the demonstrated consumer defect.
3. **Convert invalid values to None or False.**
   - Pro: keeps the caller available.
   - Con: invents missingness or an ordinary verdict and can conceal invalid
     evidence rather than reporting it.

## Decision

Keep the empty-history return and financial_safety call in their existing order.
After safety succeeds, inspect present latest.net_income followed by
latest.operating_cash_flow using math.isfinite. Raise plain ValueError naming the
first invalid field and financial distress before either sign comparison. None
remains valid but cannot hide another invalid present operand. Preserve finite
native operations, sign/ratio thresholds, reason text/order and global schemas.

## Consequences, verification and reversal

Distress verdicts cannot erase these nonfinite operands into booleans. Availability
is deliberately stricter on malformed present input, even when another condition
would make distress impossible. Existing safety source errors and finite-derived
ValidationError retain precedence. The provider still evaluates the consumer
outside acquisition recovery, so its error propagates without None fallback.
Existing hunt error handling is unchanged; no skip/recovery policy is added.

Older rows, unrelated fields/scorers, finite ratio precision, economic denominator
domains, PIT/period identity and source truth remain outside this correction.
No model field, estimator, threshold, search/gate identity, accounting-v14,
generated record or frozen-cohort change occurs.

Require actual pre-code RED for both operands and both consumers, missing peers,
error precedence and short/gapped histories. Include finite/None native truth
Hypothesis controls, ignored old inputs, safety-first source/overflow controls
and provider acquisition controls. Replay all 865 frozen payloads and the whole
module AST outside the exact guard/math import; preserve the original test file.
Obtain independent final review and foreground make check-all before safe
individual publication and exact CI verification.

Remove only the guard and math import to reverse. FINDING-339 then reopens;
historical erased evidence is not reconstructed.
