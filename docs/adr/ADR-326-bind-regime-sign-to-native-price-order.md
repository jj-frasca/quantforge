# ADR-326: Bind regime sign to native price order

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Codex autonomous session 5, ISO 2026-W43
- **Extends:** ADR-012/178/318/319/320/323
- **Resolves:** FINDING-275

## Context

Positive complete native integer prices can lose distinctions in pandas
pct_change. Forty descending prices 2**60-i, with window20, publish forty bull
bars rather than twenty warmup bull and twenty bear. Real ValidationReport
accepts the finite summary. Independent reproduction confirms int64, uint64,
Int64 and UInt64. ADR-323 validates original prices but explicitly leaves derived
trailing arithmetic separate. No observed production occurrence, leakage,
calibration impact or false graduate is established.

## Decision

Keep all original window/calendar/alignment/wealth/market checks and the original
pct_change statement. Immediately after that calculation, if
0 < window < len(market), compare mature current native price values against
lagged original native values positionally, with no float conversion or label
alignment. Refuse ValueError if this native less-than relation disagrees with
the computed mature trailing<0 relation. Use original positional slices and
native arrays without dtype conversion; Series.shift is unsuitable because its
missing prefix can itself promote integer observations to floats.

The mathematical condition uses positive validated prices: a negative trailing
return must agree with current price below its lagged price. Apply it to all
currently supported numeric dtypes rather than pretending integer observations
are the only possible precision boundary. Guard only the bear-versus-bull
partition. This does not certify trailing-return magnitude or distinguish a
rounded small positive return from exact zero; both classify as bull.

Preserve the existing trailing calculation and all native warnings and exceptions;
no errstate, catch, numerical recovery, replacement label, rounding, clipping or
source repair. Existing successful outputs remain exact when their sign agrees.
Zero horizons, genuine warmup, horizons without mature rows and empty/disjoint
intersections retain existing behavior. Preserve guard precedence, grouping,
products, Sharpe, default20 and report schema. This narrows successful evidence
instead of silently issuing a partition contradicted by its own source.

The standard PriceBar-to-frame path already converts prices to float, so this
guard cannot recover distinctions lost upstream. BacktestEngine validates positive
native inputs but does not reject this integer witness. No universal production
mitigation, source-provenance, cadence, account-policy or arbitrary huge-horizon
claim is made. Regimes remain retrospective diagnostics, with no new threshold,
selector, gate/search identity, accounting-v14, generated file or cohort change.

## Alternatives and reversal

1. Reject disagreement around existing calculations: chosen, narrow and reversible.
2. Replace every label with native endpoint comparison: mathematically plausible,
   but changes the established label algorithm rather than certifying its output.
3. Reject all integer prices or coerce them to floats: discards coherent native
   histories or erases the very source evidence needed to detect the mismatch.
4. Check original prices through Series.shift: rejected, since it can lose the
   same integer distinctions before comparison.
5. Leave a documentation caveat only: retains an executable contradicted partition.

Reverse by removing only the added sign guard and restoring the docstring,
retaining this decision and the written witness. That reopens FINDING-275.

## Verification

Write tests and observe RED before source changes. Exercise all four integer
dtypes, multiple positive horizons, first/last mature discrepancies, actual
report-entry refusal, flat/increasing/ordinary numeric controls, source
immutability, zero/oversized horizons and existing guard precedence. Hypothesis
uses independent exact integer/Fraction ordering for bounded financial cases.
Twenty-four ordinary payloads frozen before code must remain exact (baseline
SHA256 79bc99452bead95e68a9944891418e61923772e85abd7e2d7b94e642a0c5a315).
Preserve the complete prior AST except one new guard and the leading helper
docstring; shared metrics, engines, report models and gates stay byte-identical.
Independent final review, fresh foreground make check-all, explicit-path commit,
fresh fetch/rebase, immediate HEAD:master push and exact master CI are required.
