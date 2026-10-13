# FINDING-225: Integer alpha loses the OLS intercept after beta correction

- **Status:** Corrected (ADR-276)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-276

## Finding and mechanism

At base2**60, strategy[base+2,base+3,base+4] and benchmark k*[base,base+1,base+2],
k1 or3, have exact beta1/k and annual intercept504. All four plain/masked int64/
uint64 source families publish corrected beta but alpha0. Eight public failures
reproduce original means losing the intercept; published beta rounding is another
reason to compute alpha before coefficient rounding. No historical contamination
is established. This was an explicit remaining precision limitation of ADR-275.

## Correction and limits

ADR-276 computes integer alpha from exact sufficient covariance integers and
original source totals, keeping the beta ratio unrounded until the intercept's
final division. Exact constant-source beta-zero convention instead uses only
252*sumS/n and bypasses covariance. The original beta wrapper is preserved over
shared sums; the nonconstant public integer path may scan twice, without caching.

Integer alpha rounding deliberately changes family-wide and need not match
rounded published beta multiplied by rounded means. Noninteger paths, beta
outputs, excess/IR/TE/drawdown, source guards, metadata and state remain. Other
source arithmetic, final float representation and whole-comparator strict-state
limits are not certified. No threshold/calibration identity/generated record change.

## Verification

Independent scratch approved 600 centered Fraction intercept oracles across
n2–128/full uint64/large origins/both constant sides and eight public failures.
Initial unchanged-source RED observed 51 failures/1,661 preserved controls.
An explicit valid large-origin one-third-slope Hypothesis example was then added
before production to guarantee the hard edge: final RED observed 52 failures/
1,660 preserved controls. Only afterward was shared exact-sum arithmetic and
integer-only alpha dispatch implemented; no assertions were weakened.

All 2,767 affected benchmark/API tests pass. Final independent research-expert
review approved 1,712 alpha/beta tests, 600 production alpha/Fraction oracles
across n2–128/full width/constant sides, all eight corrected large intercepts,
and 540 unchanged Fraction beta oracles after refactoring. Seventy complete
ordinary/nullable/native-wide plus 32 mixed integer/float outputs remain exact
against pre-code HEAD; beta, excess, IR/TE and drawdown remain exact across 256
integer pairs. Shared loop/denominator/numerator AST matches the original beta
sufficient sums; only the intended helpers/refactor/alpha dispatch differ.
Constants bypass covariance and beta moments; original guards, state, ownership,
overlap and precision-capability fixtures pass. Full foreground `make check-all
PYTEST_WORKERS=4` passed: 8,244 backend tests, 97.70% coverage; 363 frontend
tests, 97.63% statement coverage. All verification completed before commit.
No generated records, thresholds or calibration changed.
