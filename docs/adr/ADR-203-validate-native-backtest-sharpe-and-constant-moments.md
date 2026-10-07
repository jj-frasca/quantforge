# ADR-203: Validate native backtest Sharpe and constant moments

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-142, FINDING-143
- **Supersedes in part:** ADR-185's nonfinite-native-dispersion zero convention
- **Extends:** ADR-182, ADR-183, ADR-201, ADR-202, ADR-044

## Context

The foundation Sharpe and return-moment helpers repeat the scale-failure and
rounded-constant defects corrected at CSCV and diagnostic boundaries. Their
outputs feed observed/holdout evidence and PSR, so complete finite inputs alone
do not certify native moment evidence (FINDING-142/143).

## Decision

Retain intrinsic complete real numeric validation before every shortcut. Sharpe
keeps zero for valid empty/singleton samples and exact constant observations.
Otherwise use the original pandas sample standard deviation, mean and annualized
operation order. Locally handle floating-point errors and preserve the native
answer whenever mean, positive dispersion and annualized score are finite.
Otherwise recover the same sample Sharpe from the original Series divided by
its maximum absolute observation. The common positive scale cancels in mean/std;
require finite positive normalized dispersion and finite score or raise ValueError.
Nonconstant overflow/underflow is not flat evidence. Engine financial invariants
include tiny transaction costs and must retain their full property domains.

`return_moments` recognizes exact constants before sample moments and returns None,
as already specified for constant samples. Preserve its native skew/raw-kurtosis,
count and nullable-unmeasured policy. Do not classify nearly constant observations
as flat. The interval inherits the corrected Sharpe; its iid-normal formula,
one-year minimum, confidence domain and upper-tail quantile remain unchanged.

Advance calibration accounting identity to
`whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-v8`: finite observed scores
and PSR evidence can change. Historical v5/v6/v7 remain attributable and cannot
match v8. Current distributions remain unmeasured until authorized sole-writer
refresh; no dispatch or generated-data mutation. All thresholds remain fixed.

## Verification and limits

RED native scaling/mean-overflow recovery tests, exact constant Sharpe/moment tests,
interval propagation and old-identity mismatch precede code. Independent ordinary
sample oracles protect annualization/moments; nullable/signed, short, genuine flat
and nearly constant samples preserve their domains. Existing engine/validation/
calibration gates exercise consumers. Decimal high-precision sample-score oracles
verify scaled recovery; original cost/sign properties remain unchanged. This certifies
measurability, not arbitrary
finite-result accuracy or dependence-robust interval coverage.

## Reversal

Restore former native-dispersion fallbacks, remove exact-constant guards, and
restore v7 accounting identity. That reopens FINDING-142/143.
