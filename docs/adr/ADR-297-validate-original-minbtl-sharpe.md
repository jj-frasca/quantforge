# ADR-297: Validate original MinBTL Sharpe evidence

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session21, ISO2026-W42
- **Resolves:** FINDING-251
- **Extends:** ADR-015/016/295
- **Relates to:** ADR-194/296, FINDING-252

## Context

The public minbtl_years primitive validates original trial count but not its
annualized_sharpe operand. AtN100, NaN produces NaN, positive infinity produces
zero, and booleans become numeric requirements. Other malformed sources receive
incidental errors or array-shaped results. A statistical requirement should not
accept nonfinite or non-scalar observed evidence. Normal GraduationGate report
reconstruction already provides finite Python floats, so these are standalone
synthetic boundary counterexamples, not observed production false graduates.

## Options considered

1. Validate original score at entry: closes ambiguity locally and preserves the
   numeric kernel; adds explicit refusal for formerly malformed direct calls.
2. Depend only on ValidationReport: no new validation but leaves the public
   primitive and future direct users unprotected.
3. Normalize every accepted operand to float: simplifies the kernel but changes
   Fraction and NumPy sign/arithmetic behavior. Rejected for this slice.

## Decision

After original trial-count validation and before the nonpositive-Sharpe shortcut,
require annualized_sharpe to be an original nonboolean numbers.Real scalar whose
float inspection is finite and representable. Reject otherwise with ValueError
naming annualized_sharpe. Float conversion inspects only; keep the original operand
for its existing sign comparison, square and division. Retain finite signed scores,
zero and supported NumPy/Fraction real scalars. Invalid count keeps precedence;
N1 still validates the score before its existing formula.

Preserve all accepted native arithmetic, nonpositive-score infinity, approximation,
thresholds, hashes, accountingv14 and production calibration procedure. No new
N1 shortcut, score cap, precision/scaling recovery or persisted-schema change.
Finite native squaring overflow/underflow and fixed-width integer wrap remain
explicitly unresolved in FINDING-252; source validity is not arithmetic safety.

## Consequences, verification and reversal

NaN, infinities, booleans, arrays and coercible non-real values cannot become
requirements. Valid direct operands retain their own native arithmetic, including
its existing extreme failures and warnings. Observe genuine failing source-domain
tests first, then check original Fraction/NumPy arithmetic, nonpositive infinity,
single-trial validation and count precedence. Existing Hypothesis MinBTL count/
Sharpe properties remain required. Independent research review and foreground
make check-all precede individual delivery and exact master CI verification.

Remove only the score guard to reverse; preserve FINDING-251, which would reopen.
No historical source, calibration, generated record or validation threshold changes.
