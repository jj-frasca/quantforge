# FINDING-006: DSR's null haircut is estimated from signal-contaminated trials

- **Severity:** Critical (methodology; the DSR gate has measured zero power against extreme edges)
- **Status:** Open; requires a separate evidence-backed ADR before implementation
- **Affected:** ADR-046 whole-search DSR, longitudinal and cross-sectional search

## Finding

QuantForge defines its DSR haircut as the expected maximum Sharpe **under the null**, but estimates
the haircut's `sr_std` from the current search's candidate Sharpes. Under an alternative, strategies
have heterogeneous exposure to the planted signal. The signal itself therefore widens the candidate
distribution and raises the supposed null haircut as the edge gets stronger.

The production-parity power sweep makes the consequence unambiguous: DSR passed 0/50 finalists in
all 12 planted-edge cells. At AR(1) phi +0.30, median oracle Sharpe was +3.92 and the catalog captured
77.4% in sample; all 50 finalists passed MinTRL, holdout sign, and beat-buy-and-hold, while 43 passed
PBO and 40 passed stability. None passed DSR. The composite gate therefore has zero power there
because the DSR estimator rejects every extreme edge before the other gates can matter.

## Evidence

- Diagnostic power runs 32341906980 and 32341908789: `gate_pass_counts.dsr == 0` in every 50-symbol
  AR(1) and band-reversion cell.
- Deterministic phi +0.30, seed 0: 196 candidates have cross-candidate `sr_std=1.703`; the expected-
  max haircut is 4.698 against the winning observed Sharpe 2.937, yielding DSR -1.761.
- Matching iid-null seed 0: 200 candidates have `sr_std=0.510`; the haircut is 1.410 against the
  winning observed Sharpe 0.780. The planted signal more than triples the quantity treated as null
  dispersion.
- `whole_search_deflated_sharpes` receives only current-run candidate Sharpes; no null-calibrated or
  sampling-distribution dispersion enters the calculation.

## Impact

ADR-046 correctly repaired the number of hypotheses and common cross-family price, but its chosen
dispersion estimator makes the DSR statistic alternative-dependent in the wrong direction. The
current 0% Type-I result does not rescue a test with 0% measured power at oracle Sharpe near 4.0.
Nor does this finding license restoring family-local undercounting or lowering `dsr_min`.

Until resolved, a failed DSR is evidence that the current statistic rejected the candidate, not
evidence that selection-adjusted edge is absent. PBO, stability, MinTRL, locked holdout,
beat-buy-and-hold, and ADR-018 remain independent safeguards.

## Required behavior

A separate ADR must define a null-consistent dispersion source, justify its treatment of correlated
trials and historical searches, and compare Type-I error and power against the current estimator.
Candidate approaches include a versioned null-calibrated dispersion and the sampling-moment form of
probabilistic/deflated Sharpe; neither may be selected merely because it produces graduates. The
replacement must preserve the whole-search/lifetime trial count, ship with RED tests, change
calibration identity, and pass fresh null and power calibration before production claims resume.
