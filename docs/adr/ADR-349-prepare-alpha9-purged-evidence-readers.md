# ADR-349: Prepare stable Alpha9 identity and attributed purged readers

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Codex autonomous session20, ISO2026-W43
- **Extends:** ADR-325/347/348
- **Related:** FINDING-265/272

## Context

The unsupported Alpha9 family combines local price differences with trailing
minimum/maximum sign tests. Its shipped windows are3/5/10. Independent operator
and deterministic endpoint review yields net-return hull [t-W-1,t], D=W+1,
not trailing-high's D=W. Its early signals are -d from row1; only row0 is flat.
These are existing semantics, not defects or an authorization to change them.
The reviewed pandas3.0.6 Cython extrema share the same local-operand helper,
but no Alpha9 runtime execution domain or producer support is adopted here.

The registry creates a new anonymous factory on every call, preventing exact
shipped-callable recognition. Existing persisted methods identify shifted or
trailing-high recipes, so neither can honestly attribute a future Alpha9 score.
Prepare stable identity and complete readers as one compatibility prerequisite,
with one rollback boundary and unchanged actual measurement behavior.

## Decision

Add module-owned alpha9_factory and replace only xs_alpha9's outer factory.
Retain the exact returned alpha9_signal(prices,int(p["window"])) expression,
lazy mapping lookup/coercion, mapping capture by reference, native errors and
shipped3/5/10 grid. Do not change signal, portfolio, allocation or search formulas.

Add method
`restricted-pandas-3.0.6-cython-alpha9-purged-equal-weight-continuation-v3`
and rule `rolling-alpha9-v1` to backend/API/client readers. The v3 method permits
measured or no_usable_folds only, with its exact rule and maximum lag4/6/11.
Other methods cannot carry the new rule, and v3 cannot carry a shift/high rule.
All current v1/v2 defaults, domains, original-count/finite-scalar checks,
branch/embargo/kept geometry and historical absence semantics remain.

Full trial reconstruction additionally requires xs_alpha9, exactly window and
quantile parameters, integral window3/5/10 after inherited Trial normalization,
and maximum allocated lag >=window+1. Existing parameter coercion is not replaced.
Compact readers validate attributed claims, not actual engine/source provenance.
Recognized v1/v2/v3 families may coexist with the existing complete common request,
scalar/status, paired-mean and attributed WF-bar checks unchanged.

The client preserves the new identity and renders existing measured/no-fold
geometry with a human-readable pandas3.0.6/Cython price-change-extrema qualification.
Do not display raw identifiers or invent scores. All existing noncausal training,
whole-sample family choice, mean-of-Sharpes, internal-cost/account-switching,
benchmark-cost and PIT limitations stay.

Do not change support_lag, measure_family_purged, matrix generation/runtime
capture or any evaluator. Actual Alpha9 still yields unsupported_factory.
Future producer adoption requires a separate scientific ADR/TDD, audited engine
and dependency-domain policy, before/after generation-time runtime receipts,
actual allocated maximum W+1, and actual retained-fold benchmark pairing.
No high-only method/capture rule can silently stand in for Alpha9. No threshold,
v14, fingerprint, generated file or frozen cohort change is included.

## Options and reversal

1. Combined identity/reader prerequisite: chosen; both enable a separately
   attributed future recipe without changing current measurement. Extra readers
   remain unused by production until the separate scientific decision.
2. Name/grid-only recognition: cannot distinguish substituted callables.
3. Reuse high-v2: misstates both operator chain and lag.
4. Couple producer adoption here: expands a compatibility slice into runtime
   attribution and scientific measurement; defer it explicitly.

Before producer adoption, reverse the factory replacement and new reader branches
together. After producer adoption, preserve historical readers and generated
records even if future production support is reversed.

## Verification

Observe failing identity/reader/client tests before source edits. Preserve exact
factory outputs, lazy errors/mapping behavior and warmup; test v3 measured/no-fold,
method-rule/lag/family/finalist forgeries, v1-v2-v3 mixed stores/API/client claims,
immutable/unchecked copies and actual producer refusal. Hypothesis covers allocated
hull coverage. Preserve all old tests, source/producer AST and full frozen primary
payloads (except existing run UUID/time), unchanged fingerprints and data bytes.
Independent research/frontend review and foreground make check-all precede
individual publication and exact master CI. No scientific search/cohort/provider
measurement is authorized beyond deterministic unit fixtures.
