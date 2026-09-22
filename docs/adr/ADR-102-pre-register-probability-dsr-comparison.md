# ADR-102: Pre-register and preserve the probability-DSR gate comparison

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 5 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-034
- **Extends:** ADR-036/041/053 (matched Type-I error and power), ADR-054 (probability-form DSR),
  ADR-080/096/101 (per-symbol calibration identity and probability capture)

## Context

ADR-054 deliberately kept the production gate on its selection-adjusted Sharpe margin until the
paper's probability-form DSR had matched Type-I-error and power evidence. ADR-096 and ADR-101 now
capture the selected finalist's probability on the null and planted-edge sides, but FINDING-034
shows that these marginal values are insufficient: changing one component of a conjunction must be
evaluated jointly with the other five component verdicts on the same symbols. Aggregate pass counts
cannot recover that intersection, and rejected experiments do not expose the locked-holdout score
needed to re-judge ADR-018 survival.

The analysis rule must also be fixed before future populated artifacts are inspected. Choosing a
probability cutoff after observing its false-positive and detection curves would turn calibration
into threshold tuning.

## Decision

### Preserve one complete verdict per searched symbol

Add a shared, immutable `CalibrationSymbolVerdict` to both calibration artifacts. Each record
contains the symbol, selected finalist's nullable probability-form DSR, complete incumbent
`GateResult`, locked-holdout Sharpe, and locked-holdout bar count. Null calibration stores these
records through its existing symbol-addressed diagnostics. Power calibration adds a canonical
symbol-addressed list and retains ADR-101's probability list only as a validated compatibility
projection. Legacy artifacts remain readable but explicitly unmeasured.

This record is sufficient to re-judge, without rerunning a search:

1. incumbent composite passage (`GateResult.passed`);
2. candidate composite passage, replacing only `dsr_ok` with the pre-registered probability rule;
3. ADR-018 survival at the artifact's own searched-symbol count.

### Pre-register one candidate rule

The only candidate rule is **strictly `probability > 0.95`**. This is the conventional 95%
probability reading already used as ADR-054's reporting reference. No threshold sweep chooses a
winner; other cutoffs may be printed descriptively only after this decision is closed.

The future decision uses fresh ordinary calibration artifacts with identical search/gate identity
and history on both sides. It is readable only when every successfully searched symbol has a finite
probability and a complete symbol verdict, with at least 200 observations in each null mode and the
existing 50 observations in every pre-registered AR(1) cell. Band-reversion cells remain diagnostic
because ADR-061 shows their achievable edge is below the detection frontier.

Switching the production DSR component requires all of the following on the same artifacts:

1. **No Type-I regression:** zero candidate composite graduates in each of `iid_normal` and
   `bootstrap:SPY`, and no candidate ADR-018 survivor.
2. **No strong-edge regression:** at `phi=-0.30` and `phi=+0.30`, candidate composite detections and
   ADR-018 survivors are each no lower than the incumbent counts in the same cell.
3. **Evidence of benefit:** pooling those two directional strong-edge cells, the candidate has more
   composite detections than the incumbent and the exact one-sided paired McNemar test rejects equal
   detection at `alpha=0.05`.

If any condition fails or is unmeasured, the margin gate stays. Passing these conditions authorizes
only a later gate-change ADR and matched recalibration; this ADR does not change a threshold.

`compare_probability_dsr_gate` implements this boundary without loading files itself. It refuses
the wrong null modes, gate/search/history drift, missing joint verdicts, fewer than 200 successful
symbols per null, fewer than 50 per strong-edge cell, or either missing strong-edge direction. Its
output preserves the per-cell incumbent/candidate counts, discordant paired counts, exact p-value,
and final conjunction so the first qualifying read cannot reinterpret the rule.

ADR-103 closes FINDING-035 by binding the nested cells and verdicts counted here to their advertised
container identity and by refusing duplicate strong-edge cells.

### No measurement in this unit

Do not dispatch calibration merely to populate the additive records, do not infer historical
probabilities or verdicts, and do not edit `data/*.json`. Future ordinary sole-writer runs may
populate the schema. The first read of qualifying artifacts must apply the fixed rule above.

## Alternatives considered

- **Analyze the captured probability distributions alone.** Rejected: that measures one marginal
  component, not the composite pipeline.
- **Choose the best cutoff from a ROC curve.** Rejected: it spends calibration data to tune the
  threshold and has no pre-stated error budget.
- **Use `probability > 0.50`, the closest analogue of a positive margin.** Rejected: it treats any
  more-likely-than-not result as sufficient confidence and discards the literature-facing meaning
  gained by implementing the probability form.
- **Require only equal or better aggregate power.** Rejected: opposite-direction cells can mask a
  regression, and unpaired aggregate counts cannot show whether the same symbols changed verdict.
- **Store only `other_components_pass`.** Rejected: preserving the component vector and structured
  holdout inputs keeps attribution and ADR-018 re-judgment auditable.

## Consequences

- Future artifacts can measure the actual counterfactual gate, not an unpaired proxy.
- The threshold and decision rule are fixed before any populated calibration probability is read.
- Existing artifacts remain valid evidence for the incumbent procedure and explicitly cannot answer
  the candidate question.
- Production behavior, hashes, thresholds, generated data, and cloud execution remain unchanged.

## Reversal

Remove the additive symbol-verdict records and their compatibility validation. ADR-096/101's
probability fields remain, but they again support only marginal component summaries and cannot
justify a gate switch.
