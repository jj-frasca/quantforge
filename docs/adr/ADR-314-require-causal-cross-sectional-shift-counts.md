# ADR-314: Require causal cross-sectional shift counts

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 31, ISO 2026-W42
- **Resolves:** FINDING-264
- **Extends:** ADR-024/025
- **Relates to:** ADR-144/295

## Context

Cross-sectional source functions accept negative shift periods. A negative
momentum lookback or skip can read future prices; residual momentum skip and
Alpha19 change_lag have the same issue. The public forward scorer reconstructs
these functions from a position's parameters and can publish earlier equity
that changes when only future prices change. The shipped grids use positive
windows, and no historical production occurrence or affected graduate is known.

## Options Considered

1. Validate shift-producing counts at their signal boundaries.
   - Pro: protects direct use and registry reconstruction with a small shared guard.
   - Con: direct callers relying on coercible or negative periods must correct them.
2. Restrict forward parameters to shipped grids.
   - Pro: excludes negative windows in forward reconstruction.
   - Con: leaves direct functions unsafe and unnecessarily bans causal custom windows.
3. Trust the one-bar execution lag.
   - Pro: no compatibility change.
   - Con: execution lag cannot repair signals already built from future prices.

## Decision

At entry, use existing require_trial_count(minimum=0) to validate and normalize
momentum lookback and skip, reversal lookback, residual momentum skip, and
Alpha19 change_lag. Original direct-function values must be nonboolean Integral
scalars; normalize to Python int before momentum adds its two periods, avoiding
fixed-width wrap into a negative shift. Zero periods remain valid causal inputs.
No new helper, registry/grid/schema policy, or other rolling-window validation.

Registry factories retain their existing int conversions: the source guards
inspect those resulting periods and reject negatives; they do not certify the
original factory argument's type or fractional identity. Arbitrary user-supplied
signal functions remain responsible for causality. Preserve all existing signal
formulas, ranking, execution lag, cost, scoring, selection and gate operations.
No longitudinal fingerprint, v14 accounting, threshold, data or calibration change.
Static fundamentals remain explicitly as-of snapshots, not point-in-time history.

## Consequences and verification

Malformed periods refuse before reading a panel, including empty panels. Python
and NumPy nonnegative integers retain native signal formulas with mathematical
integer shift sums. Very large supported counts may still refuse downstream
pandas representability; this decision promises no arbitrary-size pandas indexer.
Observe RED before implementation for negative/fraction/bool inputs and public
forward reconstruction. Include Hypothesis prefix/future perturbation invariants,
zero-period controls and all shipped registry configurations. Independently review
source/tests/finding, run foreground make check-all, publish individually and watch
exact master CI. No search or calibration cohort is created by these checks.

## Reversal

Remove the five validation assignments and helper import; reopen FINDING-264.
This restores unsafe direct negative-period behavior and is not recommended.
