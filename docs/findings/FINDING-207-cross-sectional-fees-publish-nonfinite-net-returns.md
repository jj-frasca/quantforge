# FINDING-207: Cross-sectional fees publish nonfinite net returns

- **Status:** Corrected — ADR-258 native source/output guards
- **Date:** 2026-10-11
- **Severity:** High — public portfolio return kernel publishes undefined accounting
- **Scope:** cross-sectional portfolio_returns original cost and final net boundary
- **Decision:** ADR-258

## Evidence

NaN cost yields NaN net returns. Positive infinity yields negative infinity on
exposed bars and NaN on truly flat bars; both costs also accept empty history.
Finite cost 1e308 overflows under reversing two-leg turnover. These calls bypass
the existing negative-cost check. Sharpe already raises on nonfinite returns;
this finding concerns published raw kernel output, not a false-zero metric.
Independent review reproduced the cases and compared 35 native valid baselines.

## Correction and required evidence

ADR-258 validates original native cost finiteness without replacing its operand,
retains the original negativity comparison, and refuses nonfinite final native
net results or native arithmetic overflow. Preserve bool, ordinary Fraction
object-dtype accounting, finite wide-cost empty outputs and huge finite flat
outputs. Do not narrow costs or add arbitrary bounds. Observe RED before code,
independently review compatibility, and complete the full foreground gate.
No generated record, workflow, cohort or validation claim has been changed.

## Observed verification

The pre-implementation run recorded 10 failures and 15 preserved cases. Added
actual Fraction/wide overflow probes and an independent Hypothesis two-leg
turnover oracle preserve the original accounting domain. The initial full gate
exposed a helper typing error; native Rational/Decimal/float/NumPy branches fixed
it without conversion or type suppression.

Fresh W42 session 2 independent review approved the final typed helper: 102
focused tests passed; 108 native baseline outputs matched exactly, including
dtype/index; 10 formerly nonfinite outputs were refused. Ten actual overflow
probes preserved NumPy error state, and five further invalid-cost empty-history
probes were refused. Unsupported native mixed arithmetic remains unsupported.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,199 backend tests
at 97.75% coverage and 363 frontend tests at 97.63% statement coverage, with all
lint, formatting and type checks green.
