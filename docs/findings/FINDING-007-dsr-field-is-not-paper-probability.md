# FINDING-007: The reported DSR is not the paper's Deflated Sharpe Ratio statistic

- **Severity:** High (methodology naming and omitted uncertainty correction)
- **Status:** Resolved by ADR-054 (2026-08-20) — the probability form is implemented, every
  user-facing claim now names the margin correctly, and every new trial records the probability
  beside the margin. What remains is a THRESHOLD question (should the gate use it?), which charter
  §4 requires be argued with a measured Type-I error and power curve, not with this finding
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

## Resolution (ADR-054, 2026-08-20)

Both of the required behaviours were taken, not one of them.

- **Implemented**, per option 1: `probabilistic_sharpe_ratio` (Eq. 1, raw-kurtosis convention,
  guarded against a degenerate estimator variance) and `deflated_sharpe_probability` (PSR against
  the existing calibrated expected-maximum haircut), with a Hypothesis invariant that the result is
  always in [0, 1] — the invariant that distinguishes it from the margin's `DSR <= observed`.
- **Renamed in every claim**, per option 2's substance: `ValidationEngine`'s interpretation
  messages, the About glossary, the Validation Report term and tooltip, the README, and
  `deflated_sharpe`'s own docstring now say *selection-adjusted Sharpe margin*, and "Deflated Sharpe
  Ratio" refers only to the probability.

Deliberately NOT done, and why: the stored field keeps its name (a schema migration across 3,237
committed pool files buys a name, while the defect was in what the name claimed), and the gate still
gates on the margin at `dsr_min` (a gate change is a threshold change, which charter §4 forbids
arguing without evidence — and it would have invalidated ADR-051's matched Type-I and power runs in
the same commit). Recording the probability per trial WAS the precondition for making that case with
measurements instead of argument, and it now happens on every search: a `Trial` carries both
numbers, priced from the same search at the same haircut, so their disagreement rate can be measured
on real trials rather than assumed. The remaining open question is therefore no longer this finding
— it is whether the gate should switch, which needs a fresh Type-I error and power curve for the new
statistic (all three calibration workflows re-dispatched together, per `validation-methodology.md`
§7.2).
