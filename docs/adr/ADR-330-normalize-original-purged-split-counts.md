# ADR-330: Normalize original purged split counts before geometry

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 8, ISO 2026-W43
- **Resolves:** FINDING-277
- **Extends:** ADR-039/198/295

## Context

The standalone purged splitter accepts NumPy unsigned scalars but performs
boundary arithmetic on them. With N8/K2 and uint32/64 embargo2, subtraction
wraps and the first training set contains its own test block. Unsigned N or K
can similarly contaminate subsequent boundaries. ADR-198 rejects these folds
at evaluation; ADR-325 normalizes panel request counts upstream. No accepted
leaky score, production occurrence or false graduate is established.

## Options Considered

1. Normalize original nonboolean Integral counts using the shared ADR-295 helper.
   Keeps NumPy integral compatibility and exact Python geometry, but refuses
   previously coercible/nonintegral inputs earlier.
2. Reject every non-Python int. Simpler type boundary, but needlessly excludes
   supported signed and unsigned integral scalars.
3. Rely on evaluator rejection. Avoids a change, but leaves the public splitter
   violating its own embargo contract and can produce misleading engine flags.

## Decision

Immediately before each existing check, use require_trial_count(minimum=0):
n_splits before n_splits<2, embargo before embargo<0, n_obs before n_obs<n_splits.
Retain the existing checks and their geometry precedence, remainder, fold sizes,
arrays and endpoint formulas. Every count is a Python int before any geometry
arithmetic. Original bool/NumPy bool, float, Fraction, string, complex, array and
negative counts refuse with ValueError. K0/1 still reach the old >=2 error;
N0 still reaches the old N>=K error. No rounding or clamping occurs.

## Consequences and limits

Signed/unsigned integral inputs match the same mathematical Python-int request;
formerly wrapped outputs deliberately change. Huge embargo remains valid and
can empty every training set without allocating embargo-sized arrays. No new
N/K resource bound is introduced; their existing observation-sized allocation
remains. The splitter does not certify feature dependency support, source
provenance, statistical independence or causal selection. lookback_embargo's
parameter proxy and the engine's broad evaluator-error flag are separate issues.
Defaults, scoring, selection, thresholds, accounting-v14, frozen cohorts and
generated records remain unchanged.

## Verification and reversal

TDD must observe unsigned overlap and malformed original-count failures before
runtime edits. Hypothesis compares every row to a Python-set embargo oracle
across signed/unsigned count families. Verify boundary embargo maxima, zero,
empty training sets, uneven/singleton folds, and original error precedence.
Compare 5,460 pre-change Python geometry payloads exactly and preserve the prior
module AST except the helper import, three assignments and leading docstring.
Independent review and foreground make check-all precede individual publication
and exact CI verification. Remove the import/assignments/docstring to reverse;
this reopens FINDING-277 without rewriting historical evidence.
