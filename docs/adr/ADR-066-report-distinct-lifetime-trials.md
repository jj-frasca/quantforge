# ADR-066: Report each symbol's cumulative lifetime trials once

- **Status**: Accepted
- **Date**: 2026-08-29
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-046 (candidate-level lifetime accounting), ADR-062 (sharded-hunt prior)
- **Finding**: `docs/findings/FINDING-008-pool-report-double-counts-lifetime-trials.md`

## Context

ADR-046 defines `Experiment.lifetime_trials` as a cumulative per-symbol counter and uses it for the
DSR haircut and MinTRL. ADR-062 restores that cumulative counter in daily sharded hunts. The pool
report currently sums the cumulative value on every retained experiment, double-counting all prior
searches carried into later rows. A 10 -> 20 -> 30 history reports 60 even though the latest and
operative denominator is 30.

The pool retains multiple rows because they are scientific results, not independent denominator
fragments. Retention happens to cap the amount of inflation but cannot turn a sum of cumulative
snapshots into a count.

## Decision

`PoolReport.n_trials` is the sum of the maximum `lifetime_trials` for each distinct symbol in the
provided pool. This is the total number of lifetime candidate evaluations represented by the
per-symbol counters without counting a carried-forward trial more than once.

The dashboard must call the value the **sum of per-symbol DSR/MinTRL denominators**. There is no
single global DSR denominator: each symbol's latest search is priced against its own lifetime count.

No experiment schema, stored row, gate input, validation threshold, or generated `data/*.json`
changes. The correction is computed at report time and is legacy-safe because old rows already
carry their best available lower-bound `lifetime_trials` values.

## Alternatives considered

1. **Sum every row as today.** Rejected: cumulative snapshots overlap by definition.
2. **Sum `Trial.n_evaluated_configs`.** Rejected: pool retention discards old non-graduate rows, so
   the result falls when evidence is pruned and omits the historical lower bound preserved in
   `lifetime_trials`.
3. **Use only the newest row per symbol.** Usually equivalent, but weaker than the maximum: clock
   skew, legacy resets, and pre-ADR-062 rows can make creation order disagree with the highest
   denominator. The store contract deliberately uses maximum for the same reason.

## Consequences

- The public trial headline falls to the count the gate actually represents.
- ADR-062's corrected monotonically increasing counters no longer inflate the report once per
  retained experiment.
- Historical generated data remains untouched.

## Reversal

Restore the sum over every experiment. That intentionally restores FINDING-008's double-counted
methodology claim.
