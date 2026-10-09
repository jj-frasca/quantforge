# ADR-232: Validate original reference cost evidence before shortcuts

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 22, ISO 2026-W41
- **Resolves:** FINDING-182
- **Extends:** ADR-055, ADR-223, ADR-229

## Context

The explicit-drift AR helper validates original cost evidence, but generic and
historical reference entries only compare cost with zero before short-history
handling. Boolean costs therefore act as numeric charges; NaN and positive
infinity can yield measured-looking zero scores on short complete histories.
Derived arithmetic checks cannot validate a scalar bypassed by that shortcut.

## Options Considered

1. Apply the established original finite-real-nonboolean scalar guard at the
   shared scorer before existing negativity and short-history branches. This
   aligns entry contracts; malformed direct calls now fail explicitly.
2. Validate only in wrappers. This misses generic band and other direct callers.
3. Coerce bool/string costs or cap finite costs. Convenient but changes original
   evidence or rejects representable native accounting; neither is justified.

## Decision

oracle_sharpe_of invokes the existing _finite_leaf_score contract on original
cost_rate before comparing it with zero or constructing returns. Cost must be
finite, real, nonboolean and float-representable; original negativity comparison
remains, including exact negative values that would round to signed zero.
Historical AR delegates through that boundary; explicit AR keeps its existing
source-law/cost guards and precedence.

Validate without substituting the converted value into arithmetic: retain the
original valid cost operand, native turnover/accounting, gross default zero,
finite huge-cost flat cases and ADR-229 derived-result refusal. Do not add a cost
cap, prediction-source policy, reference method/default replacement, threshold,
fingerprint or generated-data change. Original scalar validity does not promise
that every mixed numeric dtype or extreme derived calculation is measurable.

## Verification

Observe invalid original generic/historical costs before code, including boolean,
nonfinite and nonreal short-history evidence. Preserve exact ordinary scores and
native numpy cost operands, finite negative refusal, short/empty complete prices,
flat finite huge-cost scoring and all current explicit-AR behavior. Include an
independent scalar turnover-accounting Hypothesis oracle over ordinary costs.
Require independent final review and full foreground make check-all before the
explicit-path commit, fresh sync, individual push and exact master CI watch.

## Consequences and reversal

Invalid scalar accounting cannot obtain a reference score through a short-history
shortcut. No artifact corruption or revised detection result is inferred. Remove
the added validation call to reverse this decision, reopening FINDING-182.
