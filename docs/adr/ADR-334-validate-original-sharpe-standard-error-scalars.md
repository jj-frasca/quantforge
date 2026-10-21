# ADR-334: Validate original Sharpe standard-error scalars

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 8, ISO 2026-W43
- **Resolves:** FINDING-282
- **Extends:** ADR-043/292
- **Relates to:** ADR-296/297

## Context

The public sharpe_standard_error checks only years<=0 before its formula.
Infinite history returns zero uncertainty; booleans become ordinary finite
score/history values and NaN evidence can return NaN. Infinite history is a
mathematical limit, not finite observed track-record evidence. The inverse
frontier and reference consumers perform additional checks and use ordinary
native floats; no affected production result or rate is established.

ADR-292 deliberately preserved shared SE while repairing the inverse frontier.
This separate ADR extends the deferred original-scalar domain; it does not
reinterpret the prior preservation promise or change the statistical model.

## Options Considered

1. Validate original finite nonboolean Real leaves without replacing operands.
   Establishes evidence identity and preserves native finite formulas, but
   tightens boolean/coercible/unsupported wider input domains.
2. Convert every operand to float. Simpler computation, but erases original
   identity and changes native arithmetic beyond this finding.
3. Trust consumers' finite-output checks. No shared change, but zero uncertainty
   from infinite history and boolean evidence can remain finite.

## Decision

Add one private inspection-only helper requiring original nonboolean
numbers.Real and finite binary64 inspection, translating inspection overflow/
ValueError into ValueError. It returns no replacement value. Validate
holdout_years first, retain the existing original years<=0 error/check next,
then validate original signed Sharpe. Keep the exact return expression and
native operands unchanged. No Decimal/string/complex/array coercion is added.

## Consequences and limits

Valid signed/zero/native NumPy/Fraction evidence retains its existing arithmetic;
some wider finite values outside binary64 inspection refuse conservatively.
Original negative fractions use their original sign, including values whose
float inspection rounds to signed zero. History is finite and strictly positive;
Sharpe may have either sign. Existing default frontier/report/reference inputs
and v14 estimators remain unchanged; no threshold or rate claim follows.

Derived native overflow, integer-square wrap and final arithmetic integrity are
separate and remain open. In particular NumPy int8 scores still wrap under the
unchanged expression in this unit. Do not describe this input-boundary repair as
fixing those estimates. Zero Sharpe has a legitimate zero square, and tiny
floating square underflow can leave the additive-one SE measurable; MinBTL's
strict-positive-square policy cannot be copied here.

## Verification and reversal

Observe invalid original-scalar RED before runtime edits. Test both operands'
NaN/infinity/bool/coercible/nonreal/array refusals, year-before-score precedence,
original positivity and accepted signed/zero/NumPy/Fraction controls. Hypothesis
retains the model's ordinary signed symmetry and history scaling. Preserve 60
frozen native scalar outcomes and 24 frontier payloads plus every prior module
AST statement except the helper/import/calls/docstring. Known wrapped scalar
controls prove stage-one compatibility only, not correctness. Independent review,
foreground make check-all and individual publication/exact CI are required.
Reverse the helper/import/calls to reopen FINDING-282 without rewriting records.
