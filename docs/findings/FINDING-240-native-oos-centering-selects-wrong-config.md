# FINDING-240: Native OOS centering selects the wrong configuration

- **Status:** Corrected by ADR-291
- **Date:** 2026-10-14
- **Scope:** Walk-forward and purged-CV scalar selection/test/control Sharpes

## Reproduction

Let ordered offsets be
`[[5,5],[6,9],[14,13],[7,14],[7,10],[6,12],[3,9],[15,4]]` and
`performance = .01 + offsets * ulp(.01)` as original Float64.
Train on rows 0:4 and test on rows 4:8; purged embargo 0. Both public
evaluators choose config 1 and report OOS 2.679147472096034e16.
Exact represented Fraction variance with Decimal800 gives train config scores
2.241535595092569e16 and 2.224910874191496e16: config 0 wins. Its test
score is 1.7860983147306888e16, versus config 1's 2.688767422157616e16.
The accepted native means retained by the bounded correction agree with that
ranking; corrected config0 test score is approximately 1.786098314730689e16.

Native STD is positive finite without variance underflow. Centering the original
levels at a rounded mean inflates variance. The two score kernels remain separate
from corrected PBO and primary Sharpe. This direct synthetic fixture has valid
prefix/fold geometry; no look-ahead, real graduate or market contamination claim
follows. Large nearconstant scores expose arithmetic; they are not market claims.

## Accepted correction and limits

ADR-291 anchors only original Float64 (including byte order) whose existing
native guards accept a finite annualized score and nonzero mean, then whose
strictly same-sign range certifies exact subtraction by inclusive maxabs<=2minabs.
Normalized difference STD retains ddof1; separated exponents preserve the actual
accepted native mean. All failed native arithmetic still refuses first. Independent
matrix/control flags preserve other original dtype results despite float64 kernel
conversion. Geometry, ties, dropped folds, benchmark windows and aggregation stay.

The correction does not certify arbitrary native numerator accuracy, universal
correct rounding or exact ranking of arbitrarily close ties. Outside certificate,
constant/singleton and other source paths retain existing behavior. Both
diagnostics are stored and walk-forward is a nondefault selector, requiring new
v14 procedure identity. Historical v13/v12/v11 and frozen v10 remain attributable;
current distributions remain unmeasured. No threshold, source-law, cohort,
generated data or workflow changes.

## Evidence

Parent public reproduction independently matched prior scratch receipts.
Required research-expert scope review confirmed both wrong selections, 140
signed ordinary/nearconstant Fraction variance/Decimal200800 known-native-mean
cases (max relative error 3.72e-16), 192 exact subtraction endpoints and outside
native guards. This scope receipt preceded the public RED and production verification below;
it does not itself claim a completed full gate.

Actual final public baseline observed 99 failures and 161 preserved controls before
production. The new tests and six strict current-version pins preceded the code;
historical restoration remains independently pinned. Only then were the shared
certificate helper, independent source flags and v14 identity implemented.
The first focused run passed 997 tests and exposed two legacy assertions that
expected inaccurate source-level centering. Both original fixtures and positive
assertions were retained and strengthened to independent exact Fraction variance
with the accepted native mean and Decimal800. Isolated published-HEAD evaluation
observed two genuine failures against that oracle; the final focused 375 tests
passed. No financial property domain or validation threshold was reduced.

Independent final production review verified 240 Fraction variance/agreeing
Decimal200800 known-native-mean cases (maximum relative error 2.26e-16),
162 exact comparisons with published HEAD for outside/source/refusal/geometry/
mask behavior, and first-index ties. AST restoration certified the original
scalar arithmetic prefix and entire evaluators except new provenance assignments
and scorer keywords. Primary Sharpe and PBO production files stayed byte-identical.
The unchanged legacy fixture's independent score is 2.215111855260454e17;
both corrected helpers match exactly. Final test deltas were independently approved.
Realistic 7400x200 five-window cost increased approximately 15.4% walk-forward
(.0637 to .0735s) and 12.7% purged CV (.0855 to .0964s); all-eligible adversarial
inputs increased 85.7% and 76.3%. These are local timings, not latency guarantees.

Full foreground `make check-all PYTEST_WORKERS=8` passed 11,311 backend tests
(97.38% coverage) and 363 frontend tests (97.63% statements), with Ruff lint/format,
strict mypy, ESLint and TypeScript green. All local verification and independent
review checks were closed before commit.
