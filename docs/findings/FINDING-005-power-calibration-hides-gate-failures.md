# FINDING-005: Power calibration hides which gate components destroy power

- **Severity:** High (methodology observability; a zero-power result is not actionable)
- **Status:** Fix proposed in ADR-049
- **Affected:** ADR-041/042/045 power calibration and both power drivers

## Finding

`PowerCalibration` records only the final number of graduates. It discards the finalist's
`GateResult`, even though that result already contains six independent component verdicts. A zero
detection rate therefore cannot distinguish an edge rejected by DSR from one rejected by PBO,
parameter stability, MinTRL, holdout sign, or failure to beat buy-and-hold.

This became material after ADR-046 through ADR-048 changed trial accounting and capped the search.
Fresh production-parity runs measured 0/50 detections in every AR(1) and band-reversion cell,
including a trending process with median oracle Sharpe +3.92 and median in-sample capture 77.4%.
The artifact proves that the composite gate has no measured power there, but cannot say why.

## Evidence

- Runs 32340042967 and 32340043401 each completed six 50-symbol cells with zero detections.
- The emitted JSON contains detection, oracle, capture, and lineage fields but no gate-component
  verdicts or rejection attribution.
- A deterministic local reproduction for `phi=+0.30`, seed 0 selected an observed Sharpe +2.94
  finalist that passed PBO, MinTRL, holdout, and beat-buy-and-hold, but failed DSR (-1.76) and
  stability (0.386). That diagnosis exists on `Experiment.best_gate_result` and is discarded by
  `measure_power`.

## Impact

The current result cannot support a principled follow-up. Changing the candidate allocator,
strategy catalog, sample length, or DSR dispersion estimator would address different mechanisms.
Guessing from the aggregate risks tuning the search or a threshold merely because the funnel is
empty, which the autonomy charter explicitly forbids.

## Required behavior

Power artifacts must count, across every successfully searched symbol, how many finalists pass
each unchanged gate component. Drivers must print those counts beside the composite detection
rate. Legacy artifacts must remain readable and explicitly expose no attribution rather than
inventing it. The change is diagnostic only: no gate threshold or verdict may change.
