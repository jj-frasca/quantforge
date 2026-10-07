# ADR-199: Validate OOS diagnostic return evidence

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 13, ISO 2026-W41
- **Resolves:** FINDING-135, FINDING-136
- **Extends:** ADR-038, ADR-039, ADR-189, ADR-197, ADR-198

## Context

The public OOS evaluators coerce nonreal return sources to float and can interpret
missing values as flat-return Sharpe. Invalid training may yield an ordinary
finite selected-test score. PBO preflight protects ordinary engine matrices but
does not establish direct evaluator or benchmark evidence validity.

## Options Considered

1. Validate original numeric dtype and complete finite float64 evidence at both
   public evaluator boundaries, including optional benchmarks.
2. Trust upstream PBO. Direct diagnostic calls and benchmarks remain unprotected.
3. Drop, fill or coerce malformed evidence. Invents samples and control returns.

## Decision

Retain existing performance shape, nonempty split list, and benchmark shape
precedence. Materialize source arrays without numeric coercion. Before scoring,
require original dtype kind `i`, `u` or `f` for performance and present benchmark,
then use the existing float64 kernel conversion and require all values finite.
Retain original source identity long enough to reject any explicitly masked
observations; masked arrays with no missing observations remain valid.
Locally handle conversion overflow/invalid signals so refusal raises ValueError
under strict NumPy mode as well. Missing, nonfinite and nonreal evidence is never
filled, dropped or used for train selection, singleton/flat shortcuts or empty-
fold handling. Absent benchmark remains explicitly unmeasured.

## Consequences and limits

Tests fail before code, cover matrix/control source and missingness at both
boundaries, and retain complete signed/unsigned/floating, constant and singleton
inputs. Existing causal/embargo and benchmark invariants protect scoring. No
score formula, gate, threshold, diagnostic default, calibration identity,
workflow or generated record changes. Finite kernel evidence does not guarantee
accurate extreme native moments; numerical recovery is outside this decision.

## Reversal

Restore unchecked conversion and remove complete finite preflight. This reopens
both findings while upstream PBO retains its independent guard.
