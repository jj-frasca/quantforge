# FINDING-214: Infinite factor scores publish finite IC evidence

- **Status:** Corrected — original infinite IC signals refused by ADR-265
- **Date:** 2026-10-12
- **Severity:** High for direct public IC evidence
- **Scope:** Original signals at rank_ic before pairwise masking/ranking
- **Decision:** ADR-265

## Evidence

With A=positive infinity, B=positive infinity and C=0, and valid prices whose next
returns order A>B>C, rank_ic publishes approximately 0.866 through a false average
tie. Repeated defined dates also yield finite mean/IR/t-statistic summaries, despite
invalid original factor evidence. Signed infinities can originate in overflowing
price-ratio factors. No finite-input recovery or original ordering is established
by treating both unrepresentable values as an ordinary tie.

Research-expert independently reproduced this helper defect. Production search
calls portfolio_returns before IC and already rejects infinite scores under
ADR-260. No historical production, calibration or graduate contamination is inferred.
The gap remains at the public diagnostic boundary and is separate from ADR-264's
finite native-order correction and the open summary-domain finding.

## Correction and required evidence

Refuse exact signed infinities in original signals after ordered-column/checked-
price preparation and before masking/ranking. Refuse even final/unscorable dates;
preserve NaN/pd.NA, native finite range and all average-tie/correlation/summary
rules. Independent pre-code review approved 24 signed-infinity cases across native,
nullable, wide and Decimal inputs, source-error precedence, strict caller state and
exact IC series across 16 generators/45 configurations. No dtype ban, coercion,
threshold, estimator, longitudinal calibration identity or generated record change.

## Observed verification

Pre-implementation RED recorded 26 failures and eight preserved cases. The
two-line guard passed 475 affected tests. Independent final review approved 75
IC tests, 24 signed native/nullable/wide/Decimal infinity refusals under strict
NumPy state, 33 exact finite/native/missing/empty baselines and exact full IC
series across 16 generators/45 configurations. Caller inputs/error state and
column/price/calendar precedence were preserved. Removing the guard restores
the ADR-264 parent source AST exactly.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,378 backend
tests at 97.75% coverage and 363 frontend tests at 97.63% statement coverage;
lint, formatting and type checks passed.
