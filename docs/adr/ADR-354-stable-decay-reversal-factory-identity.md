# ADR-354: Give the shipped decay-reversal factory a stable identity

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session24, ISO2026-W43
- **Related:** ADR-325/346/349/351; FINDING-265/272

## Context

The shipped xs_decay_reversal factory is a newly allocated outer lambda on each
registry construction. A future restricted PCV audit cannot identify that callable
by exact module-owned identity. Names and matching parameter grids do not establish
that a caller retained the shipped recipe. Earlier stable-factory prerequisites
preserve scientific execution while enabling this recognition boundary.

Read-only triage follows pct_change into rolling.apply with a fresh np.dot callback,
not Alpha4's boolean percentile. First W signal rows are NaN. Nominal support is
W+1 including previous weights, but operative endpoints remain unproven. The
installed NumPy float-vector dot can dispatch to CBLAS/Accelerate; exact pandas
and NumPy versions alone do not settle the reviewed binary/runtime domain. Positive
finite prices also do not alone ensure finite derived returns. These unresolved
questions belong to a separate scientific adoption, not this representation change.

## Decision

Add module-owned decay_reversal_factory and replace only xs_decay_reversal's
outer build lambda with that function. Its returned expression must be exactly
`lambda prices: decay_reversal_signal(prices, int(p["window"]))`, preserving lazy
mapping lookup, int conversion, reference capture, module-global signal lookup at
call time, native errors and the shipped windows3/5/10 grid. Do not copy or bind
the mapping, validate early or alter signal, weighted callback, ranker, portfolio,
warmup or execution arithmetic. Preserve all other registry entries.

No support_lag, measurement, runtime capture, readers, API, frontend, thresholds,
fingerprints or longitudinal-v14 change. Actual decay PCV remains
unsupported_factory. Stable identity does not certify finite support, BLAS
semantics, arbitrary builds, source independence, PIT, executable switching or
panel calibration. FINDING-265 remains Open in part and FINDING-272 stays valid.
No source/cohort/provider/calibration measurement is authorized beyond controlled
deterministic synthetic unit fixtures; all generated and frozen records remain.

## Alternatives and reversal

Name/grid recognition cannot bind callable identity. Coupling scientific support
would bypass the unresolved dot/BLAS and endpoint evidence. Choose the narrow
identity prerequisite. Reverse the helper and build reference together without
changing scientific measurement or rewriting historical evidence.

## Verification

Observe an identity test failing before source edits. Require exact old/new
signals and portfolio outputs, lazy missing/deleted/mutated mappings, int timing
and native errors, module-global lookup, W-row warmup, grid preservation, tiny/
empty/long-window compatibility and unchanged unsupported producer. Hypothesis
covers bounded signal/portfolio compatibility. Preserve the exact returned-lambda
AST and whole registry AST except the declared helper and build reference.
Preserve all other tracked runtime/test/data bytes, default search/gate hashes
and complete three-case primary/WF/gate/accounting/PCV payloads except UUID/time,
frozen before implementation. Independent review and foreground make check-all
precede explicit-path individual commit, safe fresh sync, immediate HEAD:master
push and exact CI. No threshold or historical evidence changes.
