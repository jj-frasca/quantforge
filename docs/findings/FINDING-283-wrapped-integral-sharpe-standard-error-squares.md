# FINDING-283: Native integral Sharpe squares can understate standard error

- **Date:** 2026-10-21
- **Status:** Resolved by ADR-335
- **Scope:** sharpe_standard_error original integral score arithmetic

## Evidence

After the ADR-334 original scalar checks, actual standalone calls still give:

| Score | Native square | SE at one year | Exact Python-int control |
|---|---:|---:|---:|
| np.int8(100) | 16 | 1.01574900036674 | 4.5652239639769965 |
| np.int8(12) | -112 | 0.8819171036881969 | 1.1338934190276817 |
| np.int8(16) | 0 | 1.0 | 1.2279806626883454 |

Negative scores have the same problem. uint8(20) squares to144 rather than400;
int64(2**32) squares to zero; uint64(2**32+1) wraps to8589934593. Parent and
independent deterministic scratch probes cover37 dtype cases,21 wrapped and16
safe, across ignore/warn/raise NumPy policies, with12 extra floating/native
controls. No search, random draw, vendor, cohort or external service is involved.

Checking int(square) alone is insufficient: an int(3) subclass returning9.5
or Fraction(19,2) from __pow__ truncates to9, passing that check while changing
SE. The square's integral type and exact value must both agree. Exact custom
float/Fraction squares are conservatively unsupported by the proposed guard.

## Meaning and limits

A finite SE is not proof of intact arithmetic: positive, negative and zero
wrapped squares can all give finite understated values. ADR-334 deliberately
left this derived defect open. Current inverse-frontier results are Python
floats, pool_report converts its median gap to float, and ordinary capture
producers use validated float evidence with additional output checks. No actual
production occurrence, affected graduate, changed historical rate or calibration
is established. The model formula and every financial threshold remain.

Floating intermediate overflow, precision and final nonfinite/zero results are
separate open issues. Some tiny floating square underflow remains legitimate
because the SE model adds one. This finding does not justify MinBTL's separate
strict-positive-square policy here, nor certify arbitrary custom Real operators.

## Resolution

ADR-335 requires an original Integral score's native square to be Integral and
equal to the independent Python-int square, then uses the unchanged native
square in the formula. It introduces no replacement calculation or native
warning/exception policy. Actual preimplementation TDD recorded50 failures and
19 controls. Final191 focused tests pass; independent research review confirms
all finding table values,48 unaffected scalar outcomes,12 intended named
refusals,24 exact frontier reports and the prior runtime AST. Independent27
floating-policy comparisons and parent36 policy comparisons preserve native
values, errors and warnings, including still-open floating overflow outcomes.
Fresh foreground make check-all passed13,582 backend and566 frontend tests,
lint, formatting, typing and both coverage gates.
The prior60-scalar baseline includes12 wrapped rows that must intentionally
change to refusals; the other48 scalars and24 frontier reports must remain exact.
No generated record, frozen cohort, threshold, fingerprint or v14 change.
