# FINDING-007: The reported DSR is not the paper's Deflated Sharpe Ratio statistic

- **Severity:** High (methodology naming and omitted uncertainty correction)
- **Status:** Open; separate from ADR-050's null-dispersion repair
- **Affected:** `deflated_sharpe`, `ValidationReport.deflated_sharpe`, gate and UI descriptions

## Finding

Bailey and López de Prado (2014), Equation 2, define DSR as a probability: a Probabilistic Sharpe
Ratio evaluated against the multiple-testing-adjusted expected maximum. It uses the selected
strategy's sample length, skewness, and kurtosis in addition to the number and variance of trials.

QuantForge reports `observed_sharpe - expected_max_sharpe` instead. That value is a useful
selection-adjusted Sharpe **margin**, but it is not the paper's DSR probability and it omits the
paper's sample-length and non-Normal-return correction. The repository documents the adaptation as
"value form," yet user-facing surfaces call it the Deflated Sharpe Ratio and cite the primary paper
without making the divergence visible.

## Evidence

- The primary paper states that DSR is PSR with a multiplicity-adjusted rejection threshold and
  defines the statistic through the Normal CDF.
- `backend/app/validation/deflated_sharpe.py` only subtracts the expected-max haircut; it accepts no
  return count, skewness, or kurtosis.
- The repository invariant `DSR <= observed Sharpe` only makes sense for the local margin. The
  paper's DSR lies in `[0, 1]` and is not dimensionally comparable to observed Sharpe.

## Impact

The current `> 0` gate asks whether observed Sharpe exceeds its multiplicity threshold; it does not
ask for a stated probability that true Sharpe clears that threshold. MinTRL, PBO, the sealed
holdout, beat-buy-and-hold, and universe deflation remain independent safeguards, but they do not
make the metric itself a paper-form DSR.

## Required behavior

A separate ADR must either:

1. implement probability-form DSR with explicit sample moments, a versioned probability threshold,
   legacy artifact semantics, and fresh Type-I/power calibration; or
2. rename the metric everywhere to a selection-adjusted Sharpe margin and stop claiming it is the
   paper's DSR.

Do not resolve this by silently reinterpreting `dsr_min=0`: probability-form DSR is non-negative,
so that would remove the gate. ADR-050 deliberately preserves the existing margin and threshold
while repairing its signal-contaminated dispersion.
