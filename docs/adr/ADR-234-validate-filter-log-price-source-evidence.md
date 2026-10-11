# ADR-234: Validate band-filter log-price source evidence

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Resolves:** FINDING-184
- **Extends:** ADR-061, ADR-199, ADR-230, ADR-233

## Context

filtered_deviation validates some process parameters but not its observed log-price
array. Missing sources propagate to missing state estimates, which downstream
reference scoring deliberately treats as flat forecasts. Complex sources can lose
imaginary components when estimates enter the real output array. Malformed short
sources bypass the recursion entirely. A finite reference score does not certify
that the filter observed valid real prices.

## Options Considered

1. Validate original one-dimensional real numeric complete finite source evidence
   before recursion. This retains valid native estimation, but rejects malformed
   direct callers formerly accepted.
2. Rely on downstream price/prediction checks. Cheap, but missing filter estimates
   are legitimate startup predictions there, and complex components are already lost.
3. Coerce, fill or drop source observations. Convenient, but changes evidence and
   the state path; rejected.

## Decision

Require a one-dimensional original signed/unsigned integer or real floating-point
log-price array, with no masked missing observations and all values finite and
float64-representable. Validate after existing parameter checks and before recursion, retaining parameter
error precedence when both parameters and sources are malformed.
Materialization is for validation only; keep the original array in native np.diff
and state arithmetic. Do not require positive log prices: prices below one have
negative logs. Empty and singleton numeric complete sources retain empty and
first-unmeasured output, and all-false masks retain native behavior.

Do not change filter parameters, initialization, Kalman formulas, output startup,
source calendars, reference meanings/defaults, thresholds, fingerprints or records.
Derived filter arithmetic and scalar-parameter contracts remain separate audits.
This source boundary does not resolve FINDING-159's conditional-log/simple-return
or initialization/optimality qualifications.

## Verification

Observe malformed shape, dtype, missing/infinite and masked-source failures before
implementation, including empty/singleton shortcuts. Preserve numeric dtypes,
signed logs, startup, native outputs and input ownership. Add Hypothesis missing
source refusal and causal-prefix checks. Require independent research review,
full foreground make check-all, explicit commit/fresh sync/individual push and
exact master CI verification.

## Consequences and reversal

Invalid observations cannot disappear into unmeasured forecasts or lose complex
components while retaining a real effect-size claim. Direct callers must provide
valid source arrays. Remove the new source checks to reverse this decision and
reopen FINDING-184; all existing filter and reference semantics remain.
