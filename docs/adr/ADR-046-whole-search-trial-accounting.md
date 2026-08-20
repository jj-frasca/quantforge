# ADR-046: Price the whole searched hypothesis family in DSR and MinTRL

- **Status**: Accepted
- **Date**: 2026-08-19
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-014/015/016 (search, lifetime trials, gate), ADR-044 (calibration identity)
- **Finding**: `docs/findings/FINDING-002-dsr-trial-family-undercount.md`

## Context

The longitudinal search evaluates concrete parameter grids inside each strategy family, summarizes
each family with one finalist, and chooses the overall finalist from those summaries. At the current
three-points-per-parameter setting, 34 family summaries stand for 667 evaluated configurations.

The implementation counted the 34 summaries as lifetime trials. It also computed DSR independently
inside each family and selected the maximum of those family-local values. This omitted parameter
configurations from MinTRL, omitted prior searches from DSR, and omitted the final cross-family
selection from DSR. Cross-sectional search already counts configurations for MinTRL, but shares the
family-local DSR problem.

Persisting every per-bar return series or hundreds of candidate objects per experiment is not
necessary to repair the denominator and would recreate the pool-size failure ADR-032 solved. What
must be preserved is the number of hypotheses evaluated, while the complete current run is still in
memory and can supply the Sharpe dispersion needed by the project's value-form DSR.

## Decision

**Count concrete configurations and apply one whole-search DSR price before finalist selection.**

For both longitudinal and cross-sectional search:

1. Count every concrete configuration whose backtest is evaluated. Optional refinement adds its
   full resolved grid to the count.
2. `lifetime_trials = prior_trials + current_candidate_count`. Historical longitudinal counters
   remain a lower bound because old generated records cannot be reconstructed or rewritten safely.
3. Pool all current candidate Sharpes and compute one dispersion with the existing sample-standard-
   deviation rule and `1e-6` degenerate floor.
4. Recompute every family finalist's DSR with that common dispersion and the cumulative lifetime
   count. The overall finalist is the maximum observed Sharpe, equivalently the maximum repriced DSR
   because every finalist now receives the same haircut.
5. Keep one stored `Trial` per family/pass, but add a legacy-safe `n_evaluated_configs` field. The
   object is explicitly a family finalist summary, not a claim that only one hypothesis was tested.
6. The gate receives the repriced finalist report. PBO and parameter stability remain family-local:
   they diagnose the winning family's rank inversion and neighborhood robustness, while DSR and
   MinTRL price the broader selection that chose that family.

The lifetime DSR uses the current run's candidate-Sharpe dispersion as the available estimator of
trial variability while using the cumulative count for selection breadth. Old pool records did not
persist historical candidate distributions, so pretending to reconstruct a pooled historical
dispersion would be less honest than naming this approximation. Future exact historical pooling
would require a sufficient-statistics schema and a separate ADR.

Add an explicit accounting-method version to the ADR-044 search fingerprint. The resolved grid is
unchanged, but the measured procedure is not; existing null/power artifacts must therefore become
detectably stale without rewriting them.

`GateConfig.trial_budget` enforcement is not part of this decision. FINDING-003 records that
separate defect: enforcing 200 against today's 667-config default requires an allocation policy and
would change which hypotheses are searched, not merely how honestly they are counted.

No validation threshold changes.

## Alternatives considered

1. **Keep family-local DSR and only fix `lifetime_trials`.** Rejected: MinTRL would improve, but the
   DSR gate would still reset per family/run and the cross-family argmax would remain unpriced.
2. **Run one unified ValidationEngine report across heterogeneous configs.** DSR and selection PBO
   would be global, but parameter stability across unrelated strategy families has no neighborhood
   meaning. It would also replace rather than preserve useful per-family diagnostics.
3. **Persist every concrete candidate as a `Trial`.** Scientifically explicit but operationally
   wasteful: a family summary plus its evaluated count preserves the denominator, while hundreds of
   repeated metrics per symbol would multiply generated-pool size.
4. **Backfill historical counts from the current catalog.** Rejected: catalog grids changed over
   time. A precise-looking inferred count would be fabricated lineage, and local writes to generated
   data are forbidden.

## Consequences

- DSR and MinTRL finally price the hypothesis family that actually selected the finalist.
- Longitudinal lifetime counts jump from family passes to candidate configurations for new runs;
  historical counts remain explicitly conservative lower bounds.
- DSR values, finalists, graduation rates, null calibration, and power can change even though no
  threshold moved. ADR-044 fingerprinting makes the required recalibration visible.
- FINDING-003 remains open and must be resolved before the 200-trial budget can be claimed as a cap.

## Reversal

Restore family-local DSRs and family-summary lifetime counts, remove `n_evaluated_configs`, and
remove the accounting version from calibration identity. This would intentionally restore the
methodology defect documented in FINDING-002.
