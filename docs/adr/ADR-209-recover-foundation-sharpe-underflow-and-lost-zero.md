# ADR-209: Recover foundation Sharpe underflow and lost zero means

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 15, ISO 2026-W41
- **Resolves:** FINDING-151
- **Extends:** ADR-203, ADR-204

## Context

F151 reproduces finite partial-underflow dispersion and native zero means that
lose representable sample-Sharpe evidence. ADR-203's finite-result acceptance is
insufficient for those measurements. The same issues were separately corrected
for descriptive Sortino in ADR-207; foundation Sharpe changes gate evidence.

## Decision

Preserve complete finite real nonboolean validation, short-sample and exact-
constant zero conventions, and the native pandas sample mean/std operation order.
Within native mean/std/ratio arithmetic, locally raise on NumPy underflow and
route detected failure to existing positive common-scale recovery. A finite
native zero mean is accepted only when math.fsum of original float64 observations
also returns zero; nonzero evidence or fsum intermediate overflow invokes recovery.
Other native nonzero finite scores remain unchanged absent detected underflow.

Recovery uses original float64 values divided by their largest absolute value,
the pandas sample standard deviation, and the stable normalized sum. Compute
`(sqrt(252) * stable_sum / normalized_std) / n` so sample-count division cannot
erase a subnormal numerator before annualization and small dispersion rescue it.
For `[-1, smallest_subnormal, 1]`, the ratio rounds to `2.5e-323`, not zero;
with 97 added zeros it still rounds to a nonzero smallest subnormal. The
same sample ratio and annualization remain; finite positive dispersion and finite
score are required. A truly unrepresentable tiny ratio may round to zero; a
nonfinite recovered score remains ValueError. Caller error state is unchanged.

Advance accounting identity to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`.
Historical v9 measurements remain attributable to their executed revision and
cannot certify v10. A running scratch-only fixed v9 cohort is not relabeled;
current-version measurements require a separate run with its identity recorded.
No validation threshold, selector, catalog, generated record, workflow dispatch,
or paid resource changes.

## Verification and limits

Observe RED exact-float 800-digit Decimal tests for native partial underflow,
lost signed cancellation residuals, native mean underflow and normalized-recovery
cancellation and signed/permuted subnormal residuals with 3/100 observations.
Protect genuine cancellation, tiny scores legitimately rounding
to zero, preserved ordinary/near-constant native scores, nullable/narrow numeric
types, strict/ignore error modes and the original financial property domains.
Hypothesis tests cover representable cancellation-residual scales. Old identity
mismatch tests precede version change; full foreground gates certify consumers.

This detects particular failed arithmetic and lost zero evidence, not every
nonzero native reduction's accuracy or universal precision after normalization.
The iid-normal interval assumption and higher-moment unmeasured policy remain.

## Reversal

Restore native underflow-ignore acceptance, unconditional native-zero acceptance,
pandas normalized mean and v9 identity. This reopens F151.
