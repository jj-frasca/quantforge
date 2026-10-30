# ADR-411: Refuse finite-denominator terminal-value division zero loss

- **Status:** Accepted
- **Date:** 2026-10-30
- **Deciders:** Codex autonomous session24, ISO2026-W44
- **Partially addresses:** FINDING-346; other terminal arithmetic remains open
- **Extends:** ADR-022/373/409/410

## Context and options

Finite admitted custom settings can divide a nonzero terminal numerator to zero,
yielding DCF0, absent margin of safety and composite1/default screenpass. Loss also
occurs when period PV remains nonzero. Existing guards cannot see this terminal
division. No default-record or vendor incidence is established.

1. **Local finite-denominator quotient refusal (chosen).** Detects definite native
   nonzero loss without recovering values or modifying ordinary arithmetic; costs
   availability even if the omitted terminal component would be small.
2. **Exact/rescaled terminal recovery.** Could widen availability but changes
   financial arithmetic and needs a separate precision policy.
3. **Reject all zero equity or no-loop horizons.** Changes unrelated economic
   settings and cannot detect terminal loss with nonzero period accumulation.
4. **Leave the terminal term missing.** Preserves the demonstrated evidence loss
   and favorable available-component composite rather than reporting a failure.

## Decision

Replace only the terminal_value assignment with native terminal_cash_flow =
fcf_t * (1 + gt), terminal_denominator = r - gt, and terminal_value =
terminal_cash_flow / terminal_denominator, each computed once in original order.
Raise plain ValueError `terminal_value must not underflow to zero for DCF` iff
terminal_cash_flow !=0.0, terminal_value ==0.0 and the denominator is finite.
Retain all other expressions, settings, defaults, models and consumer boundaries.

Both signed quotient zeros refuse. Genuine numerator zeros, nonzero/subnormal
quotients and infinite denominators retain existing behavior. This includes an
infinite native difference of finite extreme settings, not only unchecked knobs.
Earlier native errors propagate; reached terminal refusal may preempt a later
terminal discount power error or metadata validation. The ADR-410 no-loop loss
controls now explicitly expect this terminal refusal; ordinary no-loop semantics
remain. No universal error-order or complete numerical-validity claim follows.

## Consequences, verification and reversal

Provider scoring stays outside acquisition recovery; hunts record per-symbol
failure before downstream acquisition/search, screen off or on. No catch, None
substitution, partial output, economic bound or threshold changes. Earlier
projection/multiplication loss, later terminal discount loss, cancellation,
nonzero rounding and source/PIT truth remain separate. No fingerprint, v14,
generated record, frozen cohort or historical reconstruction changes.

Write direct/composite/provider/hunt failure tests and exact Fraction/Hypothesis
invariants before source edits; retain truezero/subnormal/no-loop/infinite-
denominator/native-error controls and both existing no-loop input cases.
Replay 1,146 complete unchanged outcomes, two explicit changed target claims,
whole AST outside this assignment/guard and seven old test hashes. Require final
independent research/data review, foreground make check-all, individual fresh
sync/push and exact CI. Reverse by restoring only the original terminal_value
assignment and superseded no-loop expectations, reopening F346; keep this ADR.
