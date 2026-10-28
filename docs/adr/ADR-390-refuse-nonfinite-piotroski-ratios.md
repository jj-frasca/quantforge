# ADR-390: Refuse nonfinite computed Piotroski ratios

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session10, ISO2026-W44
- **Partially addresses:** FINDING-331; finite projection errors remain open
- **Extends:** ADR-029/117/155/389

## Context

Finite active operands can overflow their ratios, then erase ordering in score
booleans accepted by the fundamental pool. ADR-389 deliberately excludes derived
arithmetic. Independent exact-float witnesses confirm overflow, underflow and
ordinary finite rounding ties. A finite-result boundary can refuse the first
without claiming to repair the others. No actual vendor incidence is established.

## Options Considered

1. **Local finite computed-ratio refusal (chosen).**
   - Pro: stops nonfinite arithmetic before boolean erasure with unchanged native
     finite comparisons, shared helper and source availability semantics.
   - Con: stricter scorer availability; finite underflow/rounding remain unresolved.
2. **Exact rational comparison for every ratio.**
   - Pro: could preserve accepted binary64 operand ordering without overflow.
   - Con: changes ordinary finite scores too, needs separate precision/denominator
     policy and broader evidence; it would not fix source truth or F324's ROA proxy.
3. **Guard shared _ratio or convert overflow to None/False.**
   - Pro: one shared boundary or continued scoring availability.
   - Con: shared changes affect unrelated consumers; absence/zero would invent
     evidence and conceal arithmetic failure. Neither is adopted.

## Decision

After all existing eleven ratio assignments and before any score boolean, inspect
roa_t,roa_p,cfo_over_assets_t,lev_t,lev_p,cr_t,cr_p,gm_t,gm_p,at_t,at_p in that order.
Each non-None value must be finite or raise plain ValueError naming the ratio and
Piotroski F-score. Preserve computation order, all native arithmetic, earlier raw
operand guards and all None/zero/adjacency/short-history semantics. No recovery,
clamping, exact comparison, shared helper or schema change is adopted.

## Consequences

Invalid derived evidence refuses even when another missing ratio or failed signal
would conceal its effect. Latest ratios still compute/check without an adjacent
prior, matching existing consumption; prior ratios stay disabled across gaps.
Raw invalid operands still refuse first. Derived refusal now precedes later
safety/GP consumers in quality_score. Sweep scoring is outside acquisition
recovery and may abort before output; no skip/fallback or partial-output policy.
No financial threshold, search/gate, v14, generated or frozen evidence changes.
F331 stays open for finite underflow/rounding, and F324/F322 remain separate.

Write actual pre-code RED for all ratio branches, signed overflow, consumers and
error precedence. Retain and migrate ADR-389's existing overflow fixture to the
new explicit refusal, with no test removal. Include exact Fraction witnesses,
Hypothesis native finite controls, short/gap/None/zero/inactive controls and
mocked sweep refusal. Replay864 complete baseline claims and whole module AST
outside the exact new guard. Require independent final review and foreground
make check-all before safe individual publication and exact CI verification.

## Reversal

Remove only the ratio preflight loop. Preserve F331, reopening overflow acceptance.
