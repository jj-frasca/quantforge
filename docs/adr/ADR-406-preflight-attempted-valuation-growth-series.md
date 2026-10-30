# ADR-406: Preflight attempted valuation growth series

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session20, ISO2026-W44
- **Resolves:** FINDING-341 within attempted growth-series raw-input consumption
- **Extends:** ADR-022/373/381/382

## Context

Nonfinite historical cash flow can become a finite endpoint CAGR, a clamped DCF
and an accepted finite valuation record. Existing output and assumption guards
cannot reconstruct the erased input. Parent and independent research reproduce
synthetic direct and downstream witnesses; no actual vendor or admission effect
is established. Interior observations and shortcut-erased invalidity also matter.

## Options considered

1. **Preflight each attempted series in estimate_growth (chosen).**
   Gives field/year context at the selection boundary and retains inactive series.
   Tightens availability even when None/nonpositive peers used to cause fallback.
2. **Guard only the computed CAGR or endpoint operands.**
   Misses invalidity erased into fallback or ignored interior eligibility evidence.
3. **Validate every field/series globally.**
   Broadens inactive lower-priority inputs, short histories and other consumers.
4. **Convert malformed values to missingness or numerically recover them.**
   Invents availability or changes the estimator without justified evidence.

## Decision

Keep the fewer-than-two-row return first, chronology second and fiscal-label span.
Visit FCF, net income, revenue in the original order. Before _cagr for each attempted
series, inspect every present value in history order with math.isfinite. First
invalid value raises plain ValueError naming the field, fiscal year and valuation
growth. None/zero/negative peers cannot conceal present invalidity. Return on the
first qualifying finite-input series; lower-priority series remain unvalidated.
Add only this local guard, diagnostic field labels and math import. Preserve the
private helper, native arithmetic, finite eligibility, DCF clamps/projections,
assumptions, early base/shares returns, schemas and exception boundaries.

## Consequences, verification and reversal

Malformed attempted history no longer yields an ordinary CAGR or silently selects
another proxy. Availability is deliberately stricter. An earlier valid FCF series
still ignores invalid later series; short histories and chronology retain error
precedence. DCF early returns still occur before estimation. No catch/fallback,
skip, missingness substitution, output guard or numerical recovery is added.
Finite-derived overflow/underflow/rounding and single-year DCF base validity remain
separate, as do economic domains, physical periods/PIT and historical repair.
No threshold, search/gate/v14 identity, generated record or frozen cohort changes.

Require actual pre-code RED covering each attempted series/position, hidden invalid
peers, direct/downstream witnesses, field/year error order and precedence. Preserve
inactive series and finite/None native selection with Hypothesis. Replay 1,206
complete outcomes, whole scoped AST and three original test SHAs; obtain independent
final review, foreground make check-all, safe individual push and exact CI.

Remove only the local guard, labels and math import to reverse; the finding reopens.
