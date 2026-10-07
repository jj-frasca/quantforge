# ADR-179: Validate benchmark return dtypes

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-111
- **Extends:** ADR-112, ADR-167, ADR-172

## Context

The comparator converts aligned values to float for validation and drawdown but uses the original
Series for other statistics. Complex returns lose imaginary components in some calculations while
retaining them in others. Boolean and object payloads also bypass the numeric evidence contract.

## Options Considered

1. Require both source Series to have real nonboolean numeric dtype. This preserves observations
   and matches the canonical dataset and backtest input policy.
2. Coerce all source observations to float. This silently discards complex evidence or interprets
   strings/booleans as measured returns.
3. Rely on engine consumers. The public comparator also accepts direct return Series.

## Decision

Before inner alignment, require real nonboolean numeric dtype on both supplied Series using the
ADR-167 policy. Reject object/string/complex/boolean payloads with ValueError. Retain complete
nullable numeric inputs and explicitly extract missing aligned values as NaN for the finite check.
Keep all formulas, source calendar checks, minimum overlap and positive-wealth requirements.
Finite/value checks remain restricted to aligned observations; nonoverlapping numeric rows still
have no contribution to the comparison. No sorting, filling, dropping or coercion is added.

## Consequences and limits

Different statistics cannot interpret the same complex payload differently. The optional API
comparison retains its ValueError fail-soft behavior. Valid numeric partial overlap and estimator
outputs remain unchanged. Extreme finite covariance/output arithmetic is a separate audit surface;
this guard establishes input type validity, not every statistic's representability.
No validation threshold, generated data or workflow changes.

## Reversal

Remove the dtype guards. This reopens FINDING-111.
