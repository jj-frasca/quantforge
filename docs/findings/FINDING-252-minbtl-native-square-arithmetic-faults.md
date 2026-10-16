# FINDING-252: Finite MinBTL operands can fail or wrap while squaring

- **Date:** 2026-10-16
- **Status:** Open — conservative arithmetic policy not yet adopted
- **Area:** minbtl_years native positive-Sharpe arithmetic

## Reproduction

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

## Scope and next decision

These are manual standalone synthetic API counterexamples, not observed production
false graduates or a calibration measurement. Normal gate reports normalize scores
to Python float and GateResult rejects negative/NaN requirements; those downstream
guards do not establish correctness of this public primitive or eliminate abrupt
search failures on extreme finite evidence.

ADR-297's original score guard does not correct this finite arithmetic. A later
ADR must choose explicit refusal versus stable recovery, define original Integral
square-wrap detection and portable wider-floating semantics, retain ordinary native
behavior and protect caller NumPy error policy. A generic float64 inspection must
not silently claim that all finite extended-precision intermediates are unchanged.
Do not clip, cap, redraw a cohort or weaken a validation threshold.

No runtime correction, source draws, searches, generated writes or frozen-cohort
remeasurement is part of this finding. Scratch evidence and independent review
are summarized in `/tmp/qf-w42-s21-minbtl-followup.md`.
