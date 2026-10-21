# ADR-340: Refuse invalid paper sizing equity before allocation

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 12, ISO 2026-W43; independent research review
- **Extends:** ADR-021
- **Preserves:** ADR-120, ADR-169, ADR-339
- **Resolves:** FINDING-288

## Context

The paper sizer multiplies a frozen signal by equity/active-names. Negative equity
therefore reverses direction: at price 100/equity -1,000, signal +1 yields -10
shares and signal -1 yields +10. ADR-169 correctly allows account observations of
insolvency; that does not make negative equity investable capital. Nonfinite
capital can also pass empty/flat-book shortcuts without validation. No historical
negative account, affected broker target or actual order is established here.

## Options Considered

1. Require finite inspection and a nonnegative original operand before counting.
   - Pro: refuses invalid capital consistently without changing valid sizing math.
   - Con: also refuses empty/flat books and defers all subsequent execution steps.
2. Use absolute value, zero, or normalize every amount to float.
   - Pro: could continue allocation or return flat targets.
   - Con: invents capital, changes native arithmetic, or silently liquidates holdings.
3. Prohibit negative account/ledger observations.
   - Pro: could block this path upstream.
   - Con: hides valid insolvency observations and violates ADR-169's ledger purpose.
4. Validate only when an active quote is sized.
   - Pro: preserves more invalid-input shortcuts.
   - Con: capital validity and possible downstream flattening would depend on quotes.

## Decision

Before active counting, require `math.isfinite(equity)` and `equity >= 0` through
an original `equity < 0.0` refusal predicate. Raise ValueError when that guard
fails, then retain the entire existing body and original arithmetic operand.
Do not float-normalize, take absolute value, alter quotes, catch native inspection
errors or add a new scalar-type schema. Zero and signed zero remain supported.
The original comparison rejects tiny negative Fraction values even if their
finite inspection rounds to negative zero; positive underflow retains prior math.

## Consequences

Negative/nonfinite capital now refuses even with empty, flat or invalid-price
books. Unsupported types or excessively large values can raise native TypeError
or OverflowError earlier than those shortcuts. Finite nonnegative native
operations, conviction, truncation and ADR-120's NaN-price handling remain.
Wider/large amounts without supported finite inspection may conservatively refuse;
no arbitrary-precision recovery or new Decimal arithmetic support is promised.

The failure propagates through compute_targets before main can reconcile. This
also defers potential flattening orders and the later equity-snapshot append;
it is not an insolvency liquidation policy, rollback or guarantee of recording
an insolvency snapshot in that failed invocation. Account/ledger models and
recording order remain unchanged and can still represent negative observations.

Require actual RED cases before implementation, financial Hypothesis invariants,
independent native-operand compatibility and full foreground verification. Scope
review confirmed 328 target comparisons and 246 intermediate type/bit controls.
No broker/provider call, generated JSON, threshold, search identity, accounting
v14 or frozen cohort changes. Reversal removes this guard and restores the
reproduced directional reversal; use a superseding ADR for another failure policy.
