# FINDING-033: Probability-form DSR power is not persisted

- **Severity:** High
- **Status:** Resolved by ADR-101
- **Found:** 2026-09-22, Codex autonomous session 4
- **Affects:** `PowerCalibration`, `measure_power`, the ADR-054 probability-threshold question

## Finding

ADR-054 requires both a Type-I-error curve and a power curve before the graduation gate can be
considered for a switch from the selection-adjusted Sharpe margin to the probability-form Deflated
Sharpe Ratio. ADR-096 began preserving the probability for every null finalist, which supplies the
Type-I half. The matched planted-edge path still discards the same already-computed value:
`measure_power` resolves each experiment's finalist and persists its observed Sharpe and strategy
name, but not `Trial.deflated_sharpe_probability`.

Consequently, future null artifacts can measure how often a candidate probability threshold passes
noise, while committed power artifacts cannot measure how often it passes a planted edge. Re-running
the power workflows after choosing a threshold would make the evidence threshold-dependent and
would spend compute unnecessarily; existing durable power records also cannot be repaired because
the finalist return moments needed by the probability are not stored.

## Required correction

Persist the selected finalist's nullable probability, index-aligned with the existing per-symbol
power finalist fields. Keep legacy artifacts readable as unmeasured, change no threshold or gate,
and do not dispatch or rewrite generated calibration data in the implementation session.
