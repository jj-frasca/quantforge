# ADR-230: Validate reference close observations before return construction

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 22, ISO 2026-W41
- **Resolves:** FINDING-180
- **Extends:** ADR-042, ADR-055, ADR-178, ADR-223, ADR-229

## Context

The shared reference scorer calculates pct_change and drops missing returns before
checking derived arithmetic. Missing source prices can therefore disappear into
a short-history zero; negative prices produce finite scores, and complex prices
produce scores after imaginary components are discarded. AR wrappers calculate
returns before entering the shared scorer, so a shared-only guard is too late.

## Options Considered

1. Validate original closes at all three entries using one private helper.
   This enforces the existing positive real-price contract consistently, at the
   cost of rejecting malformed direct inputs previously accepted.
2. Rely on canonical dataset acquisition. This avoids another guard but direct
   synthetic/reference callers do not construct a ResearchDataset.
3. Fill/drop/coerce prices. Convenient, but invents or discards source evidence
   and may change the measured history; rejected.

## Decision

Before pct_change and short-history shortcuts, require a real nonboolean numeric
close Series with every observation finite and strictly positive. Use the same
dtype/value policy as ADR-178, including complete nullable numeric and empty
numeric histories. Preserve the original Series for native return calculation.
Apply one private checked-return helper to oracle_sharpe_of, oracle_sharpe and
ar1_conditional_mean_sign_sharpe. Missing conditional means retain their existing
flat-startup convention; missing prices are a different source-evidence defect.

Do not change cost defaults, sign/lag/turnover, sample estimator, scalar parameter
policy, reference definitions, search/gate/fingerprints or historical artifacts.
Calendar geometry and arbitrary extreme finite arithmetic remain separate audits.

## Verification

Observe failing generic and both AR entry tests before implementation, including
first/interior/last and singleton missing/nonpositive/nonfinite observations,
nonreal/coerced source dtypes and flat exposure. Preserve exact native scores,
short/empty/constant and complete nullable inputs. Include a Hypothesis property
that inserting a missing close cannot become a reference measurement. Require
independent research review and full foreground make check-all before delivery.

## Consequences and reversal

Malformed source histories fail explicitly rather than publishing invented finite
effect sizes. No committed corruption or changed calibration rate is inferred.
Remove the helper/checks and restore the original return construction to reverse
this decision; doing so reopens FINDING-180.
