# ADR-106: Make the PBO evidence boundary fail closed

- **Status:** Accepted
- **Date:** 2026-09-22
- **Deciders:** Codex autonomous session 6 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-038
- **Extends:** ADR-036, ADR-104, ADR-105

## Context

CSCV PBO ranks configurations by sample Sharpe on many balanced halves of one return matrix. Those
moments are defined only for finite observations and require at least two observations per half.
FINDING-038 shows that the current guarded division converts a contaminated candidate's undefined
Sharpe into zero, allowing a single `NaN` to move a live gate from PBO `0.000` to `0.829` without an
error. A scalar in the documented range is therefore not proof that valid evidence was measured.

The search normally constructs returns internally, but validation boundaries still have to defend
their statistical domain. Upstream correctness is not a license to reinterpret corruption, and
PBO is also a directly callable public module used independently in tests and research code.

## Decision

`probability_of_backtest_overfitting` rejects before splitting when:

1. the coerced performance input is not a two-dimensional matrix;
2. any matrix element is `NaN`, positive infinity, or negative infinity;
3. fewer than two configurations are present;
4. the split count is odd or below two, or observations cannot populate every group; or
5. the smallest balanced IS/OOS half contains fewer than two observations.

The function continues to accept finite constant columns. Their zero sample dispersion has the
existing explicit Sharpe value of zero and represents a real flat candidate, not missing evidence.
No row or candidate is dropped or imputed because doing so would silently change the searched
procedure and split geometry.

`pbo_max` remains strictly 0.5. This guard does not change the statistic on any valid finite
production input, so calibration accounting identity does not advance and existing artifacts do
not become stale. This decision does not authorize workflow dispatch or generated-data edits.

## Alternatives considered

- **Map non-finite observations to zero.** Rejected: a missing or infinite return is not evidence
  that the strategy was flat.
- **Drop contaminated rows.** Rejected: candidates would then be compared on a different history,
  and CSCV group geometry would change invisibly.
- **Drop contaminated candidates.** Rejected: removing a searched hypothesis after observing its
  returns changes the selection procedure PBO is meant to price.
- **Let NumPy warnings surface while returning a number.** Rejected: warnings are not a fail-closed
  contract and production callers can receive a gate-changing scalar.

## Consequences

- Invalid return evidence stops the validation/search call with a specific `ValueError`.
- Every returned PBO is computed from a finite matrix with measurable half-sample dispersion.
- Finite production results, thresholds, calibration identity, and persisted schemas are unchanged.

## Reversal

Remove the dimensionality, finiteness, and minimum-half guards. That would again let undefined
moments become fabricated zero Sharpes and valid-looking gate evidence, and is not recommended.
