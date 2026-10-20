# FINDING-276: Native sample STD zero contradicts unequal converted Sharpes

- **Status:** Resolved under ADR-329
- **Date:** 2026-10-20
- **Severity:** Low — native descriptive dispersion underflow
- **Related:** ADR-317/324; ADR-329
- **Reviewed helper SHA256:** 46a1aa403640fa706682ba4d4a7808c21392d29cf7134af1acde7de2a43494b2

## Independent reproduction

The finite distinct observations [1e-200,2e-200] survive Float64 conversion as
unequal values. Native sample STD returns 0 despite positive exact sample
variance. The helper consequently publishes std_sharpe 0 and stability_score 1.
[0,1e-200] and [-1e-200,1e-200] reproduce the same defect. A repository-root
reproduction using the exact converted binary64 observations is:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
from fractions import Fraction
from decimal import Decimal, localcontext
from app.validation.parameter_stability import parameter_stability
values = [1e-200, 2e-200]
exact = [Fraction.from_float(x) for x in values]
mean = sum(exact) / len(exact)
variance = sum((x-mean)**2 for x in exact) / (len(exact)-1)
assert variance > 0
with localcontext() as context:
    context.prec = 100
    print((Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt())
print(parameter_stability(values))
PY
```

Oracle STD is approximately 7.0710678118654751e-201. Exact constant
[1e-200,1e-200] has exact variance 0 and correctly gives native STD 0.
Ordinary [1,2] correctly gives STD 0.7071067811865476. The positive partial
underflow control [1e-160,2e-160] retains STD 7.0710284513028335e-161 and is
outside the zero-only correction.

Independent ignore/warn/raise policy probes confirm: ignore issues the zero
summary; warn issues it with native 'underflow encountered in square'; raise
already raises FloatingPointError at that operation. No helper policy mutation
occurs. A refusal guard must preserve these native warnings/raise exceptions.

## Oracle correction and limits

The initial parent probe centered values in 100-digit Decimal arithmetic and
spuriously obtained tiny positive variance on a constant pair. The corrected
oracle performs all centering and variance in exact Fraction arithmetic before
using Decimal only for square root. The bad initial receipt is retained under
/tmp/qf-w43-s6-stability-zero-probe-initial-decimal.json; corrected evidence is
/tmp/qf-w43-s6-stability-zero-probe.json. Independent exact-Fraction review
confirms both unequal positive variance and the constant zero control.

The existing 1e-9 CV denominator regularizer means substituting the positive
oracle STD would still round stability_score to 1 in binary64. No score/gate
flip, false graduate, production occurrence or calibration impact is established.
The evidence defect is the contradictory zero dispersion itself.

ADR-329 refuses std==0 when the existing converted array is not exactly
constant, after the existing finite mean/STD guard. It preserves all numerical
operations and adds no recovery, catch, warning suppression or NumPy policy.
Original Float64 projection collapses, positive partial underflow, finite
rounding and positive computed variance on constant observations remain separate.
No estimator, epsilon, threshold, selector, report, identity, accounting-v14,
generated evidence or cohort change is included.

The refusal is conservative: some unequal extreme subnormal arrays have a
positive exact sample STD that cannot round to a positive Float64 value.
The three recorded witnesses have representable positive oracle dispersion;
that is not promised for every future refusal. No numerical recovery is claimed.

## Verification status

Read-only independent confirmation completed. All 20 prior ordinary baseline
payloads replay exactly. A fresh baseline carries current source hashes at
/tmp/qf-w43-s6-stability-zero-baseline.json; old baseline bytes remain untouched.
ADR-329 is adopted before correction tests or runtime edits. Verification receipts follow after the required gates.

The first focused implementation run exposed the existing bounded-score
property's unconditional-success assumption on generated unequal tiny values,
including [0,1.7025527281246906e-191]. Its generator and all successful-result
assertions remain intact. The property now checks the adopted refusal using the
exact error, independent positive Fraction variance and zero native converted
STD. No input filtering, skipping or threshold relaxation is involved.

Final verification observed eight failing tests and nine passing controls before
runtime edits. All 89 focused stability tests passed, including independent
review of the full six-path change and the preserved old property generator and
successful-result assertions. The 20 frozen payloads remained exact, and the
complete prior AST matched after removing only the new guard and restoring the
leading docstring. Report, both engines, cross-sectional search, shared metrics,
gate and trial accounting remained unchanged.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13,303 backend tests
and 566 frontend tests (97.83% statements), plus lint, formatting and strict types
(`/tmp/qf-w43-s6-check329.log`). Runtime SHA256:
6112e1796473bfc8e5558cabc272bec429cdb3d9778d215ec5e3a63d087ccb38.
Fresh baseline SHA256:
af48c37a9b353f718257318c0479f7ce19ac55cef61b37d78dadce7a4c2d96b4.
The AST audit compares nodes structurally; an initial unparse-string matcher
failed on inserted parentheses and was corrected without changing runtime code.
All local verification closed before delivery.
