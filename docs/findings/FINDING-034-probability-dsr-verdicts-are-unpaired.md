# FINDING-034: Probability-form DSR is not paired with the composite gate verdict

- **Severity:** High
- **Status:** Resolved by ADR-102
- **Found:** 2026-09-22, Codex autonomous session 5
- **Affects:** ADR-054's probability-form DSR threshold decision; `NullCalibration` and
  `PowerCalibration`

## Finding

ADR-096 and ADR-101 preserve the selected finalist's probability-form DSR under the null and under
planted edges. They do not preserve that probability jointly with the same symbol's other five gate
component verdicts. Null artifacts retain only graduate records from the incumbent margin gate;
power artifacts retain only aggregate component pass counts. Neither representation can answer how
many symbols would pass the unchanged composite gate if only its DSR component used a probability
threshold.

The missing joint identity is load-bearing. Marginal counts cannot be multiplied or intersected:
the symbols that clear a probability threshold need not be the symbols that pass PBO, stability,
MinTRL, holdout, and beat-buy-and-hold. The same artifacts also omit structured holdout Sharpe for
rejected symbols, so an alternative gate's ADR-018 universe-deflation survivors cannot be
reconstructed. A threshold curve made from the newly captured probabilities alone would therefore
describe one component, not the whole pipeline whose Type-I error and power ADR-036/041 measure.

## Required correction

Persist one symbol-addressed calibration verdict containing the finalist probability, the complete
incumbent `GateResult`, and the locked-holdout Sharpe/length for every successfully searched null
and planted-edge symbol. Validate the compatibility projections against those records. Pre-register
one probability threshold and the decision criterion before reading populated artifacts; do not
dispatch calibration, rewrite generated data, or change the production gate in the capture unit.
