# ADR-395: Refuse nonzero Piotroski quotients rounded to zero

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session12, ISO2026-W44
- **Partially addresses:** FINDING-331; other finite projection errors remain open
- **Extends:** ADR-029/117/155/389/390

## Context

F331's finite-underflow witness still reaches quality and durable record scoring
after ADR-390. Assets1e308, NI1e-308 and CFO2e-308 produce two native zero ratios,
F-score1 and quality1/9, despite exact accepted-float Fraction comparisons proving
three erased positive signals. Independent research and data reviews reproduce
the actual producers without acquisition. No vendor incidence, affected historical
record, graduate or changed calibration rate is established.

## Options Considered

1. **Local zero-underflow refusal (chosen).**
   - Pro: identifies definite loss of nonzero evidence without replacing native
     ratios, scores or comparison rules.
   - Con: reduces scorer availability; nonzero subnormal projection and ordinary
     rounding ties remain unresolved.
2. **Exact rational comparison/recovery.**
   - Pro: could recover strict accepted-operand ordering in a broader domain.
   - Con: changes ordinary scores and needs a separate precision/denominator
     policy; it would not correct F324's ROA proxy or F322's source-period truth.
3. **Change shared _ratio or substitute None/False.**
   - Pro: broader consumer coverage or continued availability.
   - Con: changes unrelated scorers or conceals invalid evidence as missingness.

## Decision

Keep all current raw operand guards, eleven assignments and ADR-390's complete
finite-result loop unchanged. After that loop and before booleans, inspect all
eleven ratios in assignment order with their original numerator and denominator.
Raise plain ValueError naming the ratio and Piotroski F-score when the computed
ratio is present and ==0.0, both operands are present, and both operands !=0.0.
The message is `<ratio> must not underflow to zero for Piotroski F-score`.
Equality catches signed quotient zeros while preserving genuine signed-zero
numerators. Keep separate loops so a later nonfinite ratio still takes precedence
over an earlier rounded-to-zero ratio.

Missing/zero denominators continue to produce None. Short histories retain the
existing early zero result; gap-disabled prior ratios remain None, while latest
ratios are checked even across gaps. No approximation, clamp, score recovery,
shared helper, source/schema, economic denominator or availability fallback policy
is added. Nonzero subnormal values and ordinary ties retain their native behavior.

## Consequences and verification

Refusal propagates through quality_score and compute_fundamental_record and can
precede later safety errors or abort a sweep before shard output. Acquisition
recovery remains separate; no skip, partial-output or historical repair is added.
No ranking/search/gate threshold, fingerprint, v14, generated or frozen evidence
changes. F331 stays open beyond zero underflow; F324/F322 remain separate.

Before source edits, capture288 valid histories/864 complete producer JSON/Python
claims and the whole quality-module AST. TDD all eleven signed ratio branches
through three consumers, exact Fraction witnesses and named refusal ordering;
preserve true zeros, None/zero denominators, inactive/short/gap controls and nonzero
subnormal/ordinary-tie behavior. Retain the existing finite-projection examples
with explicit zero-underflow refusal and keep their ordinary-tie case. Extend the
existing finite-native properties to expect refusal precisely in the new domain,
retaining their generation domains and comparison assertions elsewhere. Add a fully
mocked real sweep propagation test. Replay complete baseline claims and whole AST
outside the exact new guard. Independent research/data final reviews, foreground
make check-all, safe individual publication and exact CI verification are required.

Reversal removes only this new guard, reopening zero-underflow acceptance. Retain
F331 and this ADR. Existing accepted records remain readable unchanged.
