# FINDING-118: Near-one confidence produces infinite Sharpe bounds

- **Date:** 2026-10-07
- **Severity:** Medium — valid confidence can produce nonfinite published interval evidence
- **Status:** Open — stable upper-tail quantile correction required

## Evidence

confidence=nextafter(1,0) satisfies the documented finite open interval (0,1). With complete
[-0.01,0.01]*126 returns, sharpe_confidence_interval publishes [-inf,+inf]. The intermediate
0.5+confidence/2 rounds to one before norm.ppf, although the mathematically equivalent tail
probability (1-confidence)/2 remains positive and representable. Research-expert probe confirms.

## Next action and limits

Write an ADR and failing boundary/property tests for a stable upper-tail quantile, retaining
confidence bounds and the iid-normal standard-error formula. Do not cap confidence or weaken
its domain. ADR-183's missing-count correction does not resolve this distinct numerical case.
No generated data or thresholds changed.
