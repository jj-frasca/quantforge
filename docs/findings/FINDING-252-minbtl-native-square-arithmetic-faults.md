# FINDING-252: Finite MinBTL operands can fail or wrap while squaring

- **Date:** 2026-10-16
- **Status:** Resolved — ADR-298
- **Area:** minbtl_years native positive-Sharpe arithmetic

## Pre-fix reproduction at `b4addff4`

Independent read-only parent/research-expert review of the unchanged positive-score
kernel `2*log(N)/(SR**2)` at N=2 found:

| Original Sharpe | Native intermediate | Current behavior |
|---|---|---|
| Python 1e200 | square overflow | OverflowError |
| Python 1e-200 | square underflows to 0 | ZeroDivisionError |
| np.float64(1e160) | square becomes infinity | false zero requirement |
| np.float64(1e-200) | square becomes0 | infinite requirement |
| np.int64(3037000500) | square wraps negative | negative requirement |
| np.int64/uint64(2**32+1) | square wraps to 8589934593 | incorrect positive requirement |

The NumPy floating overflow example has a representable nonzero mathematical
requirement near 1.3863e-320, so zero is erroneous here. At Sharpe 1e200,
the mathematical requirement instead rounds to float64 zero; that example
establishes a nonfinite intermediate without proving an incorrect rounded result.

The last integer case returns about 1.613859e-10 rather than the mathematical
approximately 7.515e-20. A finite-positive-denominator check alone cannot detect it.
Python Sharpe1e160 has a mathematically nonzero representable subnormal requirement
near 1.3863e-320 despite native squaring overflow, so refusing overflow deliberately
forgoes recoverable cases. N=1 with tiny positive score also fails native arithmetic
despite mathematical requirement zero. No recovery or shortcut is adopted here.

Minimal standalone reproduction (run from `backend/` using the existing environment):

```python
import numpy as np
from app.research.lab.gate import minbtl_years

for score in (1e200, 1e-200, np.float64(1e160), np.float64(1e-200),
              np.int64(3037000500), np.int64(2**32 + 1)):
    try:
        print(type(score).__name__, score, minbtl_years(2, score))
    except (OverflowError, ZeroDivisionError) as exc:
        print(type(score).__name__, score, type(exc).__name__)
```

## Governed correction and limits

These are manual standalone synthetic API counterexamples, not observed production
false graduates or a calibration measurement. Normal gate reports normalize scores
to Python float and GateResult rejects negative/NaN requirements; those downstream
guards do not establish correctness of this public primitive or eliminate abrupt
search failures on extreme finite evidence.

ADR-297's original score guard did not correct this finite arithmetic. ADR-298
separately adopts conservative refusal: inspect the original native square for
positive finite binary64 representation, compare Integral squares with exact
Python-int squares, divide the original operands and refuse nonfinite results.
Native arithmetic exceptions become ValueError. No N=1 shortcut or recovery.
Ordinary supported native operations/results retain their order and values.
Caller NumPy warnings and error settings remain unchanged.

This intentionally refuses some mathematically recoverable cases and some native
finite Fraction/wider-floating squares above or below binary64's inspection
range. It does not certify universal precision or correct rounding. Positive
scores whose division previously returned infinity now refuse as unmeasurable;
only nonpositive original scores retain the intentional infinite requirement.
No finite valid Python-float requirement changes. No threshold, configuration
hash, accounting-v14, frozen-source or generated-record changes are made, and
no calibration rate is remeasured or inferred.

## Verification

Initial test draft
observed 94 failures/69 controls. Before production changes, the parent corrected
a NumPy N=1 subnormal-square control to exercise its requested strict policy,
rather than testing it outside that context. Final pre-implementation run:
95 genuine failures/68 preserved controls in 2.77 seconds
(`/tmp/qf-w42-s21-native-final-red.log`), with the initial receipt preserved.
After correction, all 502 affected tests passed, including the new 163 cases,
exact-square Hypothesis property and existing count/scaling properties.
Scratch original evidence: `/tmp/qf-w42-s21-minbtl-followup.md`.

Independent research review initially reran all 502 affected tests successfully.
The first full gate passed 11,894 backend and 381 frontend tests. Coverage review
then showed the division-exception handler unexercised: earlier strict NumPy cases
failed at their square. Three post-green tests were added for a normal float32
square followed by quotient overflow at N=10,000, exercising ignore/warn/raise
behavior without production changes. Final focused and independent runs each
passed all 505 tests (166 new cases). These three additions are verification
enhancements, not part of the pre-implementation RED count.

Parent source/compatibility audit verified native numerator/square syntax, all
other gate syntax, and 672 exact supported finite results/types against the prior
implementation (`/tmp/qf-w42-s21-source298.json`).

Final foreground `make check-all PYTEST_WORKERS=8` completed successfully: 11,897
backend tests, 97.39% coverage; 381 frontend tests, 97.66% statement coverage.
Gate module line coverage is 100%. Ruff lint/format, mypy, ESLint and TypeScript
passed. Receipt: `/tmp/qf-w42-s21-check298-final.log`. Exact master CI is checked
after individual push.
