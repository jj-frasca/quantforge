# FINDING-107: Finite Monte Carlo paths can report an infinite mean

- **Date:** 2026-10-05
- **Severity:** Medium — representable expected return can be published as infinity
- **Status:** Resolved by ADR-175

## Evidence

With returns `[709.0, 709.0]`, one horizon day, four paths and seed 1, every generated GBM
terminal return is the same finite `8.218407461554972e307`. The risk estimator reports finite
percentiles but `expected_terminal_return=inf`. NumPy's arithmetic mean sums before division;
the four-value intermediate sum overflows even though their mean is representable and equal to
any one value. ADR-173's finite path guard does not validate summary arithmetic.

## Correction and limits

ADR-175 preserves ordinary arithmetic means and uses a scale-normalized arithmetic mean only
when the native intermediate overflows. This measures the same mean, without clipping returns,
changing paths, or discarding samples. It does not repair all possible estimation or summary
arithmetic, certify the GBM model, or imply this extreme history exists in generated evidence.
No stored data or risk/gate threshold changes.
