# ADR-317: Validate original parameter-stability evidence

- **Status:** Accepted
- **Date:** 2026-10-18
- **Deciders:** Codex autonomous session 33, ISO 2026-W42
- **Extends:** ADR-008
- **Relates to:** ADR-159/162, FINDING-268

## Context

The public parameter_stability helper casts directly to Float64 and reduces
all dimensions. Booleans, numeric text and nested arrays can consequently
produce perfect stability, and native complex arrays discard imaginary parts
before scoring. Type annotations do not validate original evidence. Ordinary
production callers compute real Sharpe lists themselves; no affected production
result or false graduate is established.

## Decision

Preserve the existing minimum-two-configurations check and its precedence.
Before array conversion, require every original iterated observation to be a
nonboolean numbers.Real with finite binary64 inspection. Explicitly reject
Python and NumPy booleans; normalize TypeError, ValueError and OverflowError
from float inspection to ValueError. Reject missing, complex, textual, nested
or otherwise unsupported leaves rather than manufacture numeric observations.

After the existing np.asarray(..., dtype=float64), require exactly one dimension
before reductions. This also refuses numeric-label DataFrames whose iteration
can yield scalar labels while conversion yields a matrix. Ordinary nested lists
and matrices already fail original-leaf inspection. This boundary does not
sandbox hostile user-defined iteration or array-conversion code.

Preserve support for ordinary Python/NumPy real scalars, integers and Fraction,
including mixed lists, tuples and one-dimensional numeric/object arrays. Decimal
and arbitrary float-coercible non-Real objects become intentionally unsupported;
the former was implicitly accepted by the old cast, so this is an explicit input
compatibility tightening. Finite original values whose Float64 inspection is
nonfinite or unrepresentable also refuse. Coherent finite projection remains
accepted; exact-real precision equivalence is not claimed.

Keep every existing numeric operation unchanged: Float64 conversion, mean,
sample standard deviation, CV with epsilon1e-9, extrema, positive fraction and
clipped reciprocal stability. Do not recover native reduction overflow or
underflow here; those finite-input arithmetic limitations remain separate.
The dataclass and direct construction, report schema, selector, gate thresholds,
search identity and accounting-v14 remain unchanged.

## Options considered

1. Validate original scalar evidence and converted shape before scoring.
   Chosen: narrowly separates supported observations from coercion artifacts.
2. Validate only Float64 array finiteness and dimensions.
   Rejected: conversion has already erased booleans, numeric strings and
   imaginary parts; it cannot establish original scalar evidence.
3. Rewrite stability with scaled moments or a different heuristic.
   Deferred: changes valid estimates and needs separate methodology evidence
   and calibration-identity consideration, beyond this input-contract defect.
4. Rely on production callers and report validation.
   Rejected: those mitigate current routes but do not protect standalone users.

## Verification

Observe failing public-helper tests before production edits, including boolean,
text, complex-array and nested/matrix coercion witnesses, missing/nonfinite
leaves, inspection errors and count precedence. Preserve signed real/Fraction
and NumPy controls and financial properties. Twenty valid pre-edit result
payloads are frozen for exact comparison, and an AST comparison must show only
guards/imports/docstring changes around the original numerical statements.
Run the full foreground backend/frontend gate and independent research review
before publication. No source/calibration searches, generated records or
threshold changes are part of this decision.

## Reversal

Remove the evidence/shape guards to restore implicit coercion, reopening
FINDING-268. Any estimator or threshold change requires a separate decision.
