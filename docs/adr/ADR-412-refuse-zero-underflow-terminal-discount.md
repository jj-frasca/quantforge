# ADR-412: Refuse final terminal-discount quotient zero loss

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session24, ISO2026-W44
- **Partially addresses:** FINDING-347; other arithmetic precision remains open
- **Extends:** ADR-022/409/410/411

## Context and options

A nonzero terminal value can divide to zero in final discounting after existing
DCF guards. Finite admitted synthetic custom settings yield DCF0/composite1 and
default value-screen pass; loss also occurs with nonzero period accumulation.
No affected default-record/vendor incidence is established.

1. **Local finite-factor quotient refusal (chosen).** Detects certain nonzero
   native evidence loss with no recovery, reducing availability even when the
   omitted term would not change final rounded accumulated equity.
2. **Exact/rescaled DCF recovery.** Potentially broadens availability but changes
   financial arithmetic and requires a separate precision policy.
3. **Reject zero total equity or extreme settings.** Misses partial loss and
   changes unrelated genuine-zero/economic-setting semantics.
4. **Leave the term silently absent.** Preserves the demonstrated loss and
   available-component composite admission.

## Decision

Replace only the final terminal accumulation expression with native
terminal_discount_factor = (1 + r) ** n, discounted_terminal_value =
terminal_value / terminal_discount_factor, then raise plain ValueError
`discounted_terminal_value must not underflow to zero for DCF` iff
terminal_value !=0.0, discounted_terminal_value ==0.0 and the factor is finite.
Otherwise accumulate equity_value += discounted_terminal_value. Evaluate each
existing operation once, retaining its order and operands. Change no other math,
models, settings or consumer exception boundaries.

Both signed zeros refuse for nonzero numerators. Genuine zero terminal values,
nonzero/subnormal quotients, infinite unchecked factors and ordinary no-loop
horizons retain native behavior. Earlier raw/period/first-terminal refusals and
native power/division errors remain; a newly reached final-discount refusal can
preempt later share or metadata errors. ADR-410's two original signed period-
subnormal cases now explicitly expect terminal-discount refusal. Keep those
inputs and add genuine-zero-terminal controls preserving signed period subnormals.

## Consequences, verification and reversal

Providers propagate the error outside acquisition fallback; hunts retain explicit
per-symbol failures before downstream acquisition/search with screening on/off.
No catch, None substitution, partial-output policy, bound or threshold changes.
Earlier multiplication/projection/subtraction loss, cancellation and nonzero
rounding remain outside this refusal. No complete exact-real/source/PIT proof,
fingerprint, v14, generated record, frozen cohort or historical repair follows.

Write failing direct/composite/provider/hunt and exact Fraction/Hypothesis tests
before source edits; preserve true zeros, signed nonzero subnormals, no-loop,
infinite-factor, native-error and earlier guard controls. Replay the pre-source
1,192 unchanged complete claims, 24 explicitly changed targets, whole AST outside
this final expression substitution and eight old test hashes. Require final
independent research/data review, foreground make check-all, individual fresh
sync/push and exact CI. Reversal restores only the original final accumulation
expression and superseded expectations, reopening F347; retain this ADR.
