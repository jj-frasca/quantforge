# ADR-410: Refuse finite-factor projected cash-flow discount zero loss

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session22, ISO2026-W44
- **Partially addresses:** FINDING-345; other arithmetic precision remains open
- **Extends:** ADR-022/373/409

## Context and options

A custom finite discount setting can round a nonzero projected flow to zero,
erasing equity before ADR-409's final-division guard. The actual composite and
custom provider can retain score1/flags[] and pass the default value screen.
Independent research/data approve a separate finite-factor period-division guard.
No default-record or vendor incidence is established.

1. **Finite-factor period quotient guard (chosen).** Identifies definite native
   nonzero loss with no recovery; reduces availability and can change later-error
   precedence while leaving other precision loss open.
2. **Recover with exact or rescaled arithmetic.** Could widen availability, but
   changes financial arithmetic and needs a separate precision policy.
3. **Reject all zero equity or all extreme settings.** Simpler, but introduces
   unsupported economic bounds or rejects genuine zeros and no-loop behavior.
4. **Check only final per-share division.** Already adopted; cannot distinguish
   equity that became zero earlier from genuine zero equity.

## Decision

Inside the unchanged projection loop, after computing fcf_t, assign
`discount_factor = (1 + r) ** t`, then
`discounted_fcf = fcf_t / discount_factor`, each once. Raise plain ValueError
`discounted_cash_flow must not underflow to zero for DCF year {t}` iff
`fcf_t != 0.0 and discounted_fcf == 0.0 and math.isfinite(discount_factor)`.
Otherwise retain `equity_value += discounted_fcf` with the same native operands.
Do not change projection, terminal, final-share arithmetic, models or settings.

Both signed quotient zeros refuse. Genuine zero fcf_t, nonzero/subnormal quotients,
infinite-factor unchecked settings, raw guards and no-loop horizons keep their
existing behavior. Power/zero-division errors before the guard propagate. A newly
identified earlier loss can now preempt a later power/arithmetic/metadata error;
explicitly test period1 refusal versus the former period2 overflow. No global
error-order or full numerical validity claim is introduced.

## Consequences, verification and reversal

Provider refusal propagates into existing per-symbol hunt errors before downstream
frame acquisition/search, screen off/on. Add no recovery, partial-output or workflow
catch. Default record settings are not the custom witness. Earlier projected zeros,
terminal loss, cancellation and nonzero rounding remain separate; no exact-real,
source/PIT or actual incidence claim follows. No threshold, fingerprint, v14,
generated record, frozen cohort or historical reconstruction changes.

TDD direct/composite/custom-provider/hunt witnesses and exact Fraction/Hypothesis
properties before source edits. Retain genuine zero flows, both-sign subnormal
quotients, no-loop and infinite-factor controls, native earlier errors and explicit
later-error precedence. Replay 1,148 complete outcomes and whole AST outside the
period factor/quotient/guard/accumulation substitution; preserve seven old test
hashes. Require final research/data review, foreground make check-all, individual
fresh sync/push and exact master CI. Reversal restores only the original native
period accumulation expression, reopening F345; retain this ADR and finding.
