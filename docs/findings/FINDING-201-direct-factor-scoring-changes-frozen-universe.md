# FINDING-201: Direct factor scoring changes frozen universe

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** Medium — direct scores can describe a different factor and benchmark
- **Scope:** score_forward frozen panel identity
- **Decision:** ADR-252
- **Prior art:** ADR-140/FINDING-071, ADR-149/FINDING-079

## Evidence

A synthetic momentum position frozen on S0 through S5 accepts a panel containing
only S0 through S3. Direct scoring returns 399 bars, factor Sharpe
2.1844346981211338 and benchmark Sharpe -1.646970912213931. The complete panel
scores 1.9678921261861615 and -0.04193846884583145 respectively. The subset has
changed both ranked factor and equal-weight benchmark under an unchanged position.
Replacing S0 with OUTSIDE or reversing the columns also produces a finite score.
Independent reproduction confirms all three mismatches in zero/nonzero-forward
branches. No permutation-invariance claim is made about the observed equal results.

The managed loop already checks exact membership/order before scoring and defers
a failed component. These are direct synthetic reproductions, not observed bad
book records, broker activity or false graduation. No actual cohort, workflow,
search, broker or generated record was changed.

## Correction and verification

ADR-252 applies the manager's exact ordered-column identity at direct scorer entry,
before calendar access and score shortcuts. Independent pre-code review approves
32 exact native complete score comparisons with four strategies, zero/nonzero
windows, two costs, present/absent evidence and caller nonmutation; all 98 current
forward tests pass under a scratch wrapper.

Before implementation, 11 membership/order/calendar-access regressions failed
while 16 preservation cases passed. All 148 affected tests pass after the two-line
entry check. Independent final review approves those tests and 64 exact complete
published-baseline score JSON comparisons across four strategies, static maps,
two price paths, two costs, present/absent evidence and zero/nonzero-forward
windows. Caller position, panel and evidence remain unchanged. Removing only
the entry check restores the published whole-module AST. The full foreground
gate passes 5,086 backend and 363 frontend tests, with 97.77% backend and
97.63% frontend statement coverage; lint and strict typing pass. No normalization,
panel transformation, calendar/price/evidence policy, estimator, schema or
threshold changes.
