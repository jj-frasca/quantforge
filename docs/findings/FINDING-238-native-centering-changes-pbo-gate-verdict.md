# FINDING-238: Native Float64 centering changes the live CSCV PBO verdict

- **Status:** Corrected by ADR-289
- **Date:** 2026-10-14
- **Scope:** Native Float64 per-config CSCV sample dispersion

## Frozen reproduction

Construct the complete finite matrix `.01 + offsets * ulp(.01)` with offsets:

```
[[7,10], [6,12], [5,5], [6,9], [3,9], [15,4], [14,13], [7,14]]
```

Public probability_of_backtest_overfitting(matrix,n_splits=4) gives 1/3, passing
the unchanged strict 0.5 gate. The same CSCV groups, average ranks and IS-tie
extension with exact Fraction sample variance give 2/3, failing. Exact variance
with the actual native means and anchored-normalized STD both reproduce 2/3.
Native moment underflow does not occur; positive finite STD was accepted.

For IS group subset (0,2), the native OOS rank contributes zero overfit while
exact variance contributes one. For subset (1,3), native selects config1 while
exact variance selects config0, changing that contribution from zero to one.
The other four contributions agree. Both root and independent research review
reproduced the exact per-split disagreement and public fraction.

Native centering uses a rounded source-level mean, inflating represented variance.
All entries in this fixture are same-sign and within a factor two in magnitude,
which certifies exact subtraction before normalized centering. The fixture was
found in a direct numerical test search at seed2026101412, attempt215; it is not
a no-edge process, power cohort or market measurement. No actual false graduate
or corrupt production artifact is established.

## Correction and limits

ADR-289 specifies original-Float64 provenance through cached subsets and anchored
STD only for finite native-accepted nonconstant columns with nonzero native mean
under that exact
translation certificate. Preserve original full-block native means/layout,
constant zero, measurability refusals, source/mask/history precedence and all
CSCV tie/rank/cache/threshold semantics. Other original families and noneligible
columns retain prior results. Partial underflow with positive native STD remains
eligible; native zero/nonfinite STD still refuses before any correction.

Ordinary eligible rounding intentionally changes. Exact represented variance
with known native means and independent rank controls bound verification; native
numerator precision and universal correct rounding/ranking are not established.
Separate primary Sharpe and diagnostic centering limitations remain unresolved.
Accounting advances to v12; current calibration distributions are unmeasured,
historical v11/frozen v10 attribution stays, and no cohorts/data/thresholds change.

## Evidence

Independent frozen fixture and split-rank proof precede code. Scope and realistic
performance approved before adoption. Actual repository baseline observed 36
failures and 36 preserved controls before production, including 68 new cases and
four strict predecessor identity pins. The pins advance to governed v12 while
retaining every financial assertion and exact historical v11 restoration. All
581 focused PBO, calibration and predecessor tests passed after implementation.

Independent final eleven-path review approved 68 new tests, 142 exact public
source/mixed/refusal/mask/state comparisons, 192 exact private exclusion/layout
controls and 288 Fraction/Decimal known-native-mean variance/translation checks.
AST restoration certified unchanged native reduction/guard prefixes, CSCV/cache/
tie/rank geometry and calibration arithmetic beyond its version. Input ownership
and NumPy state remained. Realistic 7400x200/70-subset runtime measured .17865s
before and .21698s after, approximately 21.5% overhead.

Full foreground `make check-all` passed 11,053 backend tests (97.43% coverage)
and 363 frontend tests (97.63% statements), with Ruff lint/format, strict mypy,
ESLint and TypeScript checks green. No verification remained running at commit.
