# FINDING-227: Native narrow variance corrupts benchmark neutrality

- **Status:** Corrected (ADR-278)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-278

## Finding and mechanism

Native float16 [0,0,444] compared against itself publishes beta0/alpha37312;
native float32 [1e20,2e20,3e20] gives beta0/alpha5.0399999602685335e22. Exact excess
is zero, so all output scalars remain finite and the comparisons are accepted,
instead of beta1/alpha0. Float16 [1000,2000,3000] declines on its false alpha
infinity. A scratch hypothesis that float32 same-series declined on tracking
error was corrected by direct public reproduction before ADR/code: excess is
exactly zero, so its tracking error is zero, not infinite.

Native variance rounds to float16/32 (including overflow infinity or underflow),
while covariance extracts float64. The ratio mixes independently different moment
precisions. Masked Float32 was corrected separately by ADR-277. No historical
market contamination is established.

## Correction and limits

ADR-278 extends that matched float64 variance/recovery path to native floating
benchmarks narrower than float64, preserving constants/integer/wider precedence,
original covariance, source guards, means, excess/IR/TE/drawdown and metadata.
Beta/its downstream alpha intentionally change; masked Float32 behavior remains.
No threshold, calibration identity or generated record changes.

This is the prerequisite to a separate narrow-excess zero-dispersion finding;
source means, alpha, existing strict-state limits and float16/masked-byte-integer
subtraction incompatibility remain explicitly separate. No universal precision
or whole-comparator availability claim is made.

## Verification

Independent prototype passed 1,220 public Fraction beta probes and six recovery
cases; 856 proposed tests include 40 explicit legacy TypeError controls, with no
skips. Unchanged repository RED observed 527 genuine failures and 775 preserved
controls before extending the two existing moment predicates.

All 4,069 affected benchmark/API tests pass. Final independent research-expert
review approved 1,302 combined tests, 1,220 public Fraction beta cases and six
tiny/subnormal recovery cases. Three hundred thirty-eight complete outside-path
outputs stay exact against pre-code HEAD; all 420 prior masked Float32 complete
outputs stay exact, and excess/IR/TE/drawdown stay exact in 800 newly affected
native cases. The full AST differs only by the low-width predicate and its two
substitutions, with covariance and constant/integer/wider precedence preserved.
Forty separate compatibility TypeErrors and existing strict narrow-dispersion
limits remain. A raw literal regex corrected a lint-only gate failure without
loosening the assertion. Fresh full foreground `make check-all PYTEST_WORKERS=4`
passed: 9,546 backend tests, 97.71% coverage; 363 frontend tests, 97.63% statement
coverage. All verification completed before commit. No generated records,
thresholds or calibration changed.
