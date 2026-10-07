# FINDING-118: Near-one confidence produces infinite Sharpe bounds

- **Date:** 2026-10-07
- **Severity:** Medium — valid confidence can produce nonfinite published interval evidence
- **Status:** Resolved by ADR-184

## Evidence

confidence=nextafter(1,0) satisfies the documented finite open interval (0,1). With complete
[-0.01,0.01]*126 returns, sharpe_confidence_interval publishes [-inf,+inf]. The intermediate
0.5+confidence/2 rounds to one before norm.ppf, although the mathematically equivalent tail
probability (1-confidence)/2 remains positive and representable. Research-expert probe confirms.

## Correction and limits

ADR-184 uses norm.isf((1-confidence)/2), the same Gaussian quantile evaluated from its
representable tail. Boundary and Hypothesis tests verify finite bounds and the forward erfc tail
with relative tolerance. Confidence bounds and the iid-normal standard-error formula are unchanged;
no confidence cap is added. ADR-183's missing-count correction was a separate input defect.
Very small confidence or endpoint widths below float resolution remain numerical limitations.
No generated data or thresholds changed.
