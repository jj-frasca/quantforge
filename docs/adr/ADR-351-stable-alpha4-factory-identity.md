# ADR-351: Give the shipped Alpha4 factory a stable identity

- **Status:** Accepted
- **Date:** 2026-10-23
- **Deciders:** Codex autonomous session22, ISO2026-W43
- **Related:** ADR-325/346/349; FINDING-265/272

## Context

Alpha4 is still unsupported for purged measurement. Its registry factory is a
fresh anonymous function on each registry construction, preventing exact known
callable recognition in a future restricted support audit. Names/grids alone
cannot identify a substituted factory. Prior stable factories preserve existing
execution while providing this prerequisite.

Read-only source triage identifies the actual signal path as a rolling.apply
callback counting less-than-or-equal comparisons, not pandas Rolling.rank.
Ties count fully; W-1 warmup rows remain NaN. No numerical/runtime support is
adopted by this identity change. A future audit must follow the actual callback,
NumPy reduction and admission/dispatch dependencies and prove operative endpoints.
FINDING-272 and all unsupported-family limitations remain.

## Decision

Add module-owned alpha4_factory and replace only xs_alpha4's outer lambda with
that function. Return exactly the prior lambda expression
alpha4_signal(prices,int(p["window"])). Preserve lazy mapping lookup/int coercion,
capture by reference, native errors, shipped5/9/21 grid, every signal and portfolio
output, tie behavior and warmup. Preserve all other registry entries.

Do not alter signals, callbacks, ranker, allocation, search, runtime captures,
support_lag, measurement, readers, API, frontend, thresholds, fingerprints or v14.
Actual Alpha4 continues reporting unsupported_factory. No scientific source,
cohort, provider, generated record or calibration execution is authorized.
Distinct attributed readers and a separately reviewed producer decision remain
prerequisites to any later measurement.

## Alternatives and reversal

Name/grid recognition cannot establish callable identity. Coupling new producer
support here would expand a representation change into scientific runtime/domain
adoption without completed endpoint/dependency evidence. Choose stable identity
only. Reverse the helper and outer-factory replacement together; scientific
measurement behavior is unchanged in either direction.

## Verification

Observe failing identity test before source edits. Require exact signal/portfolio
compatibility across shipped and native-coercion controls, lazy missing/deleted
keys, mapping mutation, conversion timing/errors, ties, warmup and unsupported
purged producer. Hypothesis checks bounded compatibility invariants. Preserve
the whole prior registry AST except the new helper and exact outer replacement,
including the exact old returned lambda. Preserve other runtime/tests/data bytes
and search/gate fingerprints. Independent research review and fresh foreground
make check-all precede explicit-path commit, fresh safe sync, immediate individual
HEAD:master push and exact master CI. No threshold or historical evidence changes.
