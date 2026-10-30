# FINDING-345: Nonzero projected cash flow is discounted to zero

- **Status:** Corrected within finite-factor period-division zero loss (ADR-410); other precision remains open
- **Date:** 2026-10-30, Codex autonomous session22 (ISO2026-W44)
- **Severity:** Confirmed finite-input evidence loss under custom settings; incidence unmeasured
- **Related:** ADR-022/373/409/410; separate from final per-share division loss

## Actual producer evidence

At c774d8ca, two ordinary synthetic rows with FCF1e-300, shares1, revenue100,
net income1, EPS1 and history price10, plus admitted custom settings discount1e300,
terminal0, horizon1 and flat growth, produce a nonzero native projected cash flow
but zero discounted cash flow. Fraction(native_FCF)/Fraction(native_discount_factor)
is strictly positive and below half the least binary64 subnormal. Equity therefore
accumulates to zero before ADR-409's final guard. At current price1, composite1,
margin of safety None and empty flags reach the default passing value screen.
An actual injected custom-settings provider retains that result; the universe
reaches downstream acquisition with screening off or on. Negative projected flows
also lose their sign/magnitude. No source acquisition or search is needed.

Parent and independent research/data confirm these accepted-input witnesses.
These are extreme constructed settings/scalars, not realistic corporate economics,
vendor/run incidence, an affected historical record, false graduate or trading
impact. FundamentalRecord uses defaults and takes no custom assumptions argument;
this witness does not establish an affected default record.

## Correction, availability and limits

ADR-410 computes the native period discount factor and quotient once, refusing
when nonzero projected cash flow yields zero discounted cash flow with a finite
factor. This identifies loss of nonzero native evidence; no approximate recovery,
None fallback, financial bound or validation threshold changes. Genuine zero
projected flows and every nonzero quotient, including subnormals, stay native.
Infinite factors from unchecked settings remain outside this finite-factor guard;
existing direct behavior and later composite metadata refusal remain unchanged.
Native power/division errors before the reached guard still propagate.

Immediate refusal deliberately can preempt later errors: discount1e200/horizon2
currently loses period1 then raises period2 OverflowError; the correction raises
period1's named ValueError first. No universal error-order preservation is claimed.
Earlier projection-to-zero, terminal-leg loss, accumulator cancellation, nonzero
rounding and full exact-real/source/PIT truth remain outside this correction.
Zero/nonpositive horizons keep their existing no-projection-loop behavior.

Existing provider scoring is outside acquisition recovery, and the universe
records the refusal before downstream frame acquisition/search even with screening
off. No new skip, partial-output, workflow catch or unscored policy is introduced.
Other callers propagating scorer errors retain that policy; no default-record
incidence is inferred. No generated records, fingerprints, v14 or frozen cohorts change.

## Verification

Before source edits, freeze 1,148 complete direct/composite/record outcomes, whole
module AST and seven original test hashes in /tmp/qf-w44-s22-discount-baseline.{py,json}.
This includes ADR-409 behavior, genuine zeros, subnormals, native errors, nonpositive
horizons, unchecked infinite-factor and terminal-only zero controls. Bounded replay
is no universal financial correctness proof. Actual RED, independent reviews,
foreground full gates and exact CI receipts follow below or in CODEX_RUNNING_STATE
when completed; no pending verification is claimed as passed.


Actual pre-code RED collected 42 cases: 31 failures and 11 passing controls, with
production source diff empty. The 31 targets comprised 21 missing refusals,
8 downstream-acquisition calls and 2 former later-OverflowError outcomes. Every
failure targets the agreed new behavior; no collection or expectation error was
included. After implementation, 196 focused synthetic tests pass with one existing
live test excluded and two retained serializer warnings. Ruff requested only
source error-message layout; formatting was applied after focused completion,
then lint/format and the scoped AST/outcome replay passed again.

Data independently runs all 42 new cases; research runs those plus 35 ADR-409 cases
(all 77 pass). Both independently reproduce all 1,148 complete outcomes, scoped
whole module AST and seven old test hashes exactly. Both approve the finite-factor
scope, explicit later-error precedence change and zero/subnormal/no-loop/infinite-
factor controls. A research wording correction distinguishes preserved nonzero
quotients from projected flows (nonzero projected flows with zero quotient are
the new refusal domain). No old test was edited, deleted or skipped. Required
foreground full-gate/publication/CI receipts remain in the session ledger; these
focused checks do not claim unfinished checks passed.
