# ADR-101: Persist probability-form DSR power

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 4 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-033
- **Extends:** ADR-041/053 (durable power calibration), ADR-054 (probability-form DSR), ADR-096

## Context

ADR-054 says a gate-statistic change needs matched Type-I-error and power evidence. ADR-096 makes
the candidate probability available for every searched null symbol, but its implementation stops at
`NullCalibration`. `measure_power` already obtains the identical selected `Trial` for every planted-
edge symbol and persists several of its fields in `PowerCalibration`; it discards
`deflated_sharpe_probability`. The committed power sweeps therefore cannot produce the power side of
the decision ADR-054 requires.

The value cannot be reconstructed later from the existing power artifact. Probability-form DSR
uses the selected trial's return count, skewness, and kurtosis, and those moments are not persisted.
The safe time to preserve it is while `measure_power` still holds the selected trial.

## Decision

Add `finalist_deflated_sharpe_probabilities: list[float | None]` to `PowerCalibration` and populate
it from the exact finalist already used for `finalist_observed_sharpes` and
`finalist_strategy_names`.

1. The list is index-aligned with those per-symbol finalist lists and contains one item for every
   successfully searched planted-edge symbol.
2. An item may be `None` when ADR-054 could not compute the finalist's probability. The list itself
   defaults to empty so artifacts predating ADR-101 remain honestly unmeasured.
3. No statistic is recomputed, no extra search is run, and no gate, threshold, configuration hash,
   or pass/fail decision changes.
4. Do not dispatch a calibration workflow or rewrite `data/*.json` in this implementation. Future
   ordinary power runs will populate the additive field.

## Alternatives considered

- **Infer probability from the stored finalist Sharpe.** Rejected: the return moments and sample
  count required by ADR-054 are absent.
- **Re-run power only after a probability threshold is chosen.** Rejected: the underlying
  probabilities are threshold-independent and should be preserved before examining candidate
  cutoffs, exactly as ADR-096 does on the null side.
- **Store only a pass count at one candidate threshold.** Rejected: that bakes an unevidenced
  threshold into the measurement and prevents an honest Type-I/power curve.

## Consequences

Future null and planted-edge artifacts preserve the same candidate statistic for every searched
symbol, enabling a later pre-registered ADR to compare false-positive and detection curves without
new searches. Historical power artifacts continue to validate with an empty list and remain
explicitly unmeasured for this statistic.

## Reversal

Remove the additive field and the one append in `measure_power`. Existing artifacts containing the
field remain readable because it is not part of any gate decision.
