# FINDING-099: Forward lifecycle boundaries trust invalid inputs

- **Date:** 2026-10-04
- **Severity:** High — invalid configuration or evidence can become an honest-looking hold
- **Status:** Resolved by ADR-168

## Evidence

`ExitPolicy` and `CrossSectionalExitPolicy` accept nonfinite Sharpe/drawdown thresholds, negative
grace periods, and nonpositive rolling windows. The single-name no-trade horizon also accepts
nonpositive counts. NaN comparisons are false, disabling their trigger; invalid windows change the
sample behind the advertised policy. Unchecked copies are trusted by the decision functions.

The pure lifecycle functions return holds during grace or zero trades before checking paired input
alignment or finite returns. Even when measured, mismatched calendars are compared as independent
trailing samples. Single-name negative/fractional/boolean trade counts can bypass the zero-trade
interpretation. The evaluate wrappers have additional no-forward-data early returns.

TDD regressions require malformed policies and return pairs to reject before those early returns,
and require policy copies to reject at both pure and frame/panel decision boundaries.

## Impact and limits

Current production defaults and canonical prepared data are valid; no corrupted generated book is
demonstrated. This finding concerns direct/injected decision inputs and malformed configuration.
Empty aligned history is legitimately unmeasured. Finite drawdown limits above one are deliberate
isolated diagnostic settings and must remain supported. Finite inputs alone do not certify all
extreme floating-point arithmetic; that is a separate estimator/wealth-path audit.

## Correction

ADR-168 validates policy identity and paired returns before decision branches, without altering a
valid policy's defaults or predicates, changing thresholds, or imputing missing returns.
