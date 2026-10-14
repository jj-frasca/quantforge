# FINDING-235: Level-scaled Sharpe recovery erases represented tiny dispersion

- **Status:** Corrected by ADR-286
- **Date:** 2026-10-13
- **Scope:** Foundation Sharpe, original native/classic Float64 STD underflow/collapse

## Reproduction

For signs +/-1 and n=3,4,7, construct original Float64 observations as
`sign * (1e-200 + arange(n) * ulp(1e-200))`, using native or classic nullable
Float64. All observations are finite, complete and nonconstant. Exact centered
Fraction sample variance and Decimal 200/800 annualized Sharpe agree.

The published scorer returns magnitudes 9.043156280963163e16,
7.831603069706906e16 and 4.559735594528967e16. Exact represented-sample targets
are 1.0944783154858846e17, 8.477792577323957e16 and 5.06645011621018e16:
respectively 17.3747%, 7.622% and 10.001% low. These twelve outcomes are accepted
false numerical evidence. Native variance underflows; the recovery scales levels
before centering, losing their original near-equal differences.

## Correction and limits

ADR-286 anchors represented differences before scaling and retains original-sum
evidence, restricted to finite failed Float64 STD. Ordinary estimates, nonfinite
STD, mean/ratio-only failures and other source families retain prior behavior.
Final overflow refuses; true zero and subnormal scores remain valid. Subnormal
control cases permit one output ULP, verified by exact squared-midpoint checks;
universal correctly rounded recovery is not claimed.

Search/holdout/gate consume this scorer, so accounting advances to v11. Historical
v10 fingerprint and evidence remain attributable; frozen cohorts stay untouched
and v11 distributions remain unmeasured. No generated record or validation
threshold changes. No actual false graduation or market-record contamination
has been demonstrated.

## Evidence

Independent scratch review approved twelve reproductions, 180 Fraction/Decimal
oracles, 40 cancellation/rounding controls, 24 exact squared-midpoint subnormal
checks, 308 exact outside baselines and 316 original financial tests. Draft tests
passed 102 cases against the scratch prototype and new identity, before adoption.
Adopted tests then failed genuinely on the unchanged implementation: 40 failed,
62 preserved. Independent precode review approved scope and corrected the
subnormal wording before implementation. Production focused verification passed
561 tests. The retained current-fingerprint pin first failed against the governed
v11 identity, then was updated; the new test preserves exact v10 restoration.
Backend Ruff lint/format passed. No test, threshold or property domain was weakened.

Final independent eight-path review approved 180 production Fraction/Decimal
200/800 oracles (nearconstant maximum relative error 2.22e-16), 40 rounding
controls with 24 exact squared-midpoint checks, 308 unchanged published baselines,
two arithmetic refusals and 418 new/original financial tests. Both v11 and restored
v10 fingerprints independently match. Removing only the helper and STD-local
provenance dispatch restores the prior metrics module AST. Accounting differs
only in its version; frozen evidence, thresholds and grids are untouched.
All independent checks are terminal; fresh full gate and publication follow.

Fresh foreground make check-all PYTEST_WORKERS=4 passed: 10787 backend
tests, 97.47% coverage; 363 frontend tests, 97.63% statements;
lint, format and type checks green. No generated record was edited.
