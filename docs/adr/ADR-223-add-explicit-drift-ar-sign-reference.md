# ADR-223: Add an explicit-drift AR conditional-mean sign reference

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 21, ISO 2026-W41
- **Relates to:** ADR-041, ADR-055, FINDING-155

## Context

The historical AR reference omits drift * (1 - phi) from the conditional mean
of the generator's drift-plus-centered AR process. FINDING-155 records the
opposite-sign counterexamples. A source-only additive helper was chosen before
F168 outcomes were inspected; those frozen measurements are now reported.
Changing the default would silently change the meaning of stored effect sizes.

## Decision

Add ar1_conditional_mean_sign_sharpe(frame, *, phi, drift, cost_rate=0.0).
Require explicit known source-law phi and drift, without estimation or defaults.
For observed simple returns, form phi * lagged_return + drift * (1 - phi).
Leave the first unavailable observed lag unmeasured, hence flat in the established
oracle_sharpe_of scorer. Use that scorer's existing return, turnover, cost and
sample-Sharpe conventions, without another lag.

Validate original finite real nonboolean parameters; phi must be stationary
in (-1, 1), drift float-representable, and cost finite/nonnegative. Refuse derived
nonfinite conditional means rather than passing infinite sign evidence.
The helper expects the existing finite positive close-price frame convention;
this unit does not revise the legacy generic scorer or its frame boundary.

Preserve oracle_sharpe, oracle_sharpe_of, measure_power, all artifacts, attribution,
thresholds, fingerprints, workflows and API/UI behavior. The new function is an
explicit reference-strategy measurement, not cost-aware or realized-sample
Sharpe optimality. FINDING-155 remains Open for governed production attribution.

## Options considered

1. Replace the historical rule: corrects the mean but silently restates existing
   reference meanings without schema/consumer attribution. Rejected.
2. Add an explicit helper: permits honest source-law reference calculations while
   preserving defaults; requires a separate production opt-in unit. Chosen.
3. Estimate drift from the frame: convenient but introduces fitting and possible
   future leakage into the purported known-law reference. Rejected.

## Verification

Observe RED tests before implementation. Cover both recorded sign flips,
phi zero with nonzero drift, exact zero-drift historical equivalence, first
unavailable lag, scalar turnover accounting, causal prefix invariance and invalid
original parameters. Include independent scalar/Hypothesis score invariants.
Independently review the complete diff and run the full foreground gate.

## Consequences and reversal

A caller can measure a drift-aware sign reference without relabeling historical
scores. No production measurement is corrected by merely adding the function.
Delete the unused helper and its tests to reverse this additive decision; retain
F155's historical finding and measurement qualifications.
