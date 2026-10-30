# ADR-405: Preflight latest gross-profitability operands

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session20, ISO2026-W44
- **Resolves:** FINDING-340 within raw latest-year GP input consumption
- **Extends:** ADR-029/380/384/385/389; no derived-output-finiteness decision

## Context

The standalone GP scorer can return nonfinite ratios or erase nonfinite gross
profit into None through missing/zero assets. Single-year Piotroski returns zero
by policy, so the composite can clip invalid GP into a finite score. Existing
records refuse nonfinite GP outputs, but accept the demonstrated missing-leg
cases. Parent and independent research confirm 13 synthetic controls; no actual
vendor incidence, favorable recorded score or screen effect is established.

## Options considered

1. **Preflight both present latest GP operands locally (chosen).**
   Preserves shared schemas and finite math, refusing invalidity before shortcuts.
   Availability tightens even when a peer is absent or zero.
2. **Validate only the computed ratio.**
   Would miss invalidity already erased to None or finite zero; finite-derived
   ratio overflow is a distinct output-validity decision.
3. **Make every AnnualFundamentals field finite globally.**
   Broadens unrelated consumers/provider availability and ignored-row policy.
4. **Convert invalid values into None or zero.**
   Invents missingness or an ordinary score rather than reporting invalid evidence.

## Decision

Keep empty-history None. After latest selection, inspect gross_profit followed
by total_assets with math.isfinite when present, before _ratio. Raise plain
ValueError naming the first invalid field and gross profitability. None cannot
hide a present invalid peer; zero/negative finite denominators remain supported.
Reuse the existing math import. Change no shared division, schema or caller.

## Consequences, verification and reversal

Raw GP invalidity cannot become a direct ratio, clipped score or missing leg.
Availability is deliberately stricter. Composite order remains Piotroski, GP,
safety: new single-year GP refusals can precede safety source/finite-derived
errors, while two-year Piotroski errors retain precedence. No catch/fallback,
substitution, skip policy or recovery is added. Older rows and unrelated fields
remain outside the direct guard. Record construction still propagates errors.

Finite derived overflow, underflow and ordinary rounding remain native, including
existing record output refusal. This does not establish economic denominator
validity, complete quality correctness, paper-formula/source-period/PIT truth or
historical reconstruction. No thresholds, search/gate/v14 identity, generated
records or frozen cohorts change.

Require actual pre-code RED for both fields/three consumers/missing-zero peers/
first-invalid order and error precedence. Preserve finite/None division with
Hypothesis, ignored-old-row and overflow/underflow controls. Replay 1,731 complete
frozen outcomes, whole module AST outside only the exact guard and original test
SHAs. Obtain independent final review and foreground make check-all before safe
individual push and exact CI verification.

Remove only this guard to reverse; the finding reopens, historical evidence stays.
