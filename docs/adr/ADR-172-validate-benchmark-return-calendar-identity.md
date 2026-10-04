# ADR-172: Validate benchmark return calendar identity

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28
- **Resolves:** FINDING-103
- **Extends:** ADR-112

## Context

Finite paired returns alone do not establish chronological identity. The comparator accepts
duplicate dates and unordered observations; drawdown depends on chronological adjacency. Inner
alignment can also expand duplicate labels or conceal a caller's unordered source series.

## Options Considered

1. Validate unique ascending input indexes before alignment. This preserves valid partial overlap
   while rejecting ambiguous identity rather than inventing a repair.
2. Sort and deduplicate. Sorting hides acquisition drift; deduplication needs a new observation policy.
3. Require identical full indexes. This breaks ADR-013's valid partial-overlap comparison contract.

## Decision

Require each input Series index to be unique and monotonically increasing before inner alignment.
Retain at least two finite overlapping observations, positive-wealth returns, and all formulas.
Partial overlap remains valid. Generic/naive ordered indexes remain supported; this intrinsic guard
does not certify timezone semantics or a quality check. Do not sort or drop duplicate observations.

## Consequences and limits

Malformed calendar identity raises ValueError; the optional API benchmark remains fail-soft under
ADR-013. Existing checked engine paths already carry ordered bars; this correction primarily
protects the public comparator boundary, not evidence that a committed experiment is malformed.
Valid overlap and financial results remain unchanged.

## Reversal

Remove the index guards. This reopens FINDING-103.
