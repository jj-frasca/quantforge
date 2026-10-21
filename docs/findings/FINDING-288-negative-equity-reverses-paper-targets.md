# FINDING-288: Negative sizing equity reverses frozen strategy direction

- **Status:** Resolved — ADR-340; synthetic regression and full verification passed
- **Date:** 2026-10-21
- **Scope:** `execution/sizing.py::equal_weight_targets`; ADR-021/120/169/339

## Evidence

With a supplied quote at price 100 and equity -1,000, the current sizer returns
-10 shares for signal +1 and +10 for signal -1. Fractional signals +0.5/-0.5
similarly become -5/+5 shares. The negative capital operand reverses directional
intent. Nonfinite capital also bypasses validation when no active quote reaches
arithmetic. These are deterministic synthetic inputs, not evidence of an actual
negative account, historical target/fill or real-money operation.

`AlpacaAccount` can represent negative equity, and main converts its equity to
float before sizing. ADR-169 deliberately preserves zero/negative account
observations; refusing invalid allocation capital is a distinct responsibility
from honestly recording such observations. No account or ledger model is changed.

## Correction and boundaries

ADR-340 adds a finite/nonnegative guard before active counting while retaining
the original equity operand, allocation, conviction and truncation statements.
There is no normalization, absolute value, invalid-as-zero rule or quote removal.
The original negative comparison also refuses Fraction(-1,10**400), whose finite
inspection projects to negative zero. Zero equity remains supported and flat.

This deliberately refuses invalid capital for empty, all-flat and invalid-price
books too. Unsupported types and excessive inspection ranges can produce native
TypeError/OverflowError before shortcuts; no broad original-type or arbitrary-
precision contract is added. Finite Decimal active arithmetic remains unsupported
where the existing Decimal/float multiplication raises TypeError.

The pure failure propagates before reconciliation, deferring all new orders
including possible flattening. Main's later equity-snapshot append is also not
reached. Ledger models still support negative observations, but this correction
does not establish that the failed driver invocation records insolvency. It adds
no liquidation policy, rollback, account access or historical observation rewrite.

## Verification

Independent prospective review reproduced the direction reversal and confirmed
328 native nonnegative target comparisons plus 246 intermediate type/bit checks,
including signed zero, Float32/Float64, Fraction, positive underflow, active and
inactive layouts, and ADR-120's NaN-price policy. These are scope controls, not
claimed preimplementation repository RED evidence. Actual RED/GREEN, financial
properties and final verification were completed in session 13, as recorded below.

Before the runtime edit, the new repository suite produced 63 failures and seven
passing controls (`/tmp/qf-w43-s13-equity-red.log`); the production diff was empty.
The narrow guard then passed all 70 new cases, including Hypothesis checks for
negative-capital refusal, preserved direction and truncation bounded by the
represented share quotient. This bound does not certify exact-real dollar
exposure. Combined focused verification passed 132 synthetic tests with the
existing live smoke excluded (`/tmp/qf-w43-s13-equity-green.log`).

Independent final five-path review approved the change and independently passed
97 focused cases with one live test excluded. Actual-code comparisons against
the prior revision passed 210 target outcomes, 324 native intermediate type/bit
controls, 91 invalid-capital refusals and 42 native inspection-error controls.
The prior module AST is unchanged except for the declared guard and docstring;
287 existing backend test files remain byte-identical. Receipts:
`/tmp/qf-w43-s13-equity-review.md`, `-review.json`, `-final-audit.json` and
`-parent-audit.json`. Runtime SHA256:
`f7e775b12ff9ba91cb07e15c95e63cf4523c98dbf928fa4d5e743846cfb6771f`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13,754 backend tests
(97.38% coverage) and 566 frontend tests (97.83% statements), lint, formatting
and strict types (`/tmp/qf-w43-s13-check340-final.log`). The initial full-gate
attempt stopped at test import sorting; it was corrected and the complete gate
rerun. All local verification closed before publication. Exact master CI is
verified after the individual push. No provider/broker call, generated record,
threshold, accounting-v14 or frozen-cohort change occurred.
