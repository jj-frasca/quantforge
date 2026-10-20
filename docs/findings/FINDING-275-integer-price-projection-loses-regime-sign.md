# FINDING-275: Integer price projection loses regime sign

- **Date:** 2026-10-19
- **Severity:** Low — descriptive precision at native numeric direct entry
- **Status:** Resolved under ADR-326
- **Reviewed source:** 292c9a9e, validation/regime_analysis.py::analyze_regimes
- **Related:** ADR-012/178/318/319/320/323/326

## Reproduced evidence

Forty ordered prices 2**60-i, for i=0..39, are complete positive native integers.
At window20 every mature price is below its original lagged price. Exact Fraction
ratios therefore require twenty warmup bull bars and twenty bear bars. The public
helper instead produces forty bull bars for int64, uint64, Int64 and UInt64:
pandas pct_change projects the closely spaced large integers to equal floats.
Every mature computed trailing return is zero. Solvent strategy returns
[0.01,-0.02,0.03,0.005] repeated ten times produce finite all-bull total_return
0.27499170522369343 and Sharpe5.500783643232587, accepted by real ValidationReport.
The actual supplied integer observations, rather than an intended decimal source,
contradict this partition.

Parent and independent research-expert reproductions agree on pandas3.0.6 and
NumPy2.5.4. Flat and increasing large-integer controls remain all bull; small
ordinary descending integers correctly split twenty/twenty. This distinguishes
loss of native price ordering from a calendar, horizon or warmup-policy defect.
A repository-root reproduction before correction is:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
from fractions import Fraction
import pandas as pd
from app.validation.regime_analysis import analyze_regimes
prices = pd.Series([2**60-i for i in range(40)], dtype='int64')
returns = pd.Series([.01, -.02, .03, .005] * 10)
assert all(Fraction(int(prices[i]), int(prices[i-20]))-1 < 0 for i in range(20,40))
print({k:v.n_bars for k,v in analyze_regimes(returns, prices, 20).items()})
PY
```

Before correction it prints {'bull':40}. ADR-326 requires refusal of the
contradiction; it does not silently relabel or recompute the summary.
Scratch full report/dtype/control probe:
/tmp/qf-w43-s5-regime-integer-probe.py/json. Reviewed helper SHA256:
ef64a73ae9e535cceaabc476fc45cb1bbbd072c174fdda8b213b8650b3247e33.

## Scope and correction

This is derived arithmetic, outside ADR-323's original-price validity guard.
The standard PriceBar frame conversion projects close to float before validation,
so distinctions already lost upstream cannot be recovered here. BacktestEngine
itself does not reject these valid positive native integers. No production
occurrence, future-information leakage, false graduation or historical-calibration
impact is established. Regime breakdown is descriptive and does not add a gate.

ADR-326 retains the trailing calculation and refuses a mature computed sign that
disagrees with original positional endpoint ordering. No Series.shift, float
coercion or label alignment may erase those endpoints. Native warnings/exceptions,
source checks, warmup, zero horizon and all accepted score expressions remain.
This checks only the bear/bull partition; return magnitude, positive-versus-zero
precision, upstream projection, provenance and aggregate arithmetic remain separate.
No report, shared engine, threshold, selector, accounting-v14, generated evidence
or frozen-cohort change. Verification receipts follow after the required gates.

## Verification

The pre-implementation run observed 19 failures and 25 passing controls
(`/tmp/qf-w43-s5-regime-order-red.log`). Fresh session6 independent research
review approved all five paths with 189 regime tests passing. The preservation
audit passed all24 frozen payloads and the complete prior AST after removing
only the new sign guard and docstring lines. Report, both engines, shared
metrics, gate and trial accounting remained byte-identical.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13250 backend tests
and479 frontend tests, including lint, formatting, strict types and coverage
(`/tmp/qf-w43-s6-check326.log`). Helper SHA256:
27caddf3c897d8bbe8ce3418818df6601048a6426a904d88b3bbdc36015514d4.
These controls verify this narrow refusal; they do not certify arbitrary
finite-precision arithmetic or change any historical generated result.
