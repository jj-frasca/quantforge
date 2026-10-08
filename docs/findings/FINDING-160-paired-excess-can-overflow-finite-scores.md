# FINDING-160: Paired excess can overflow finite scores

- **Date:** 2026-10-08
- **Severity:** High — derived report evidence can become nonfinite
- **Status:** Resolved under ADR-214
- **Reproduced revision:** `65307508`

`NullCalibration.paired_excess` subtracts diagnostic scores without checking
the resulting float. Both the ADR-080 symbol-paired path and complete legacy
array path return `[inf]` for finite scores `1e308 - (-1e308)`; reversing
the operands returns negative infinity. ADR-213 correctly accepts these
individual finite scores. Finite operands do not imply a finite difference.

`pool_report._excess_rows` trusts these differences as percentile input.
This is a reproduced arithmetic boundary defect, not a claim of corrupted
committed artifacts or an observed incorrect production verdict. Partial
legacy arrays remain unpairable; absent diagnostics remain unmeasured.

A bounded correction must reject nonfinite derived excess at this authoritative
pairing boundary, preserving signed finite differences, explicit/absent None,
the complete-array legacy guard and symbol pairing. It must not drop rows,
clamp scores, invent zero/None, change thresholds or rewrite generated data.
Root scalar coherence, other real-side report arithmetic and percentile
overflow are separate boundaries, not certified by this finding.

## Correction and verification

ADR-214 validates every emitted difference with the existing finite score guard.
Both overflow signs, both diagnostic families and both pairing schemas failed
before implementation: eight RED cases alongside twelve preserved cases.
All twenty then passed, followed by 341 affected calibration/report/merge tests.
Independent research review approved the correction and read all eight committed
null artifacts: 2,400 finite differences remained valid and legacy unmeasured
pairs remained None. Full foreground `make check-all PYTEST_WORKERS=4` passed
3,257 backend tests (97.54% coverage) and 359 frontend tests (97.63% statements).
