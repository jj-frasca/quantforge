# ADR-323: Require valid matched regime market prices

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Codex autonomous session 3, ISO 2026-W43
- **Extends:** ADR-012/178/318/319/320
- **Resolves:** FINDING-273

## Context

On 24 solvent strategy returns, missing, zero and boolean market prices all
produce the same finite all-bull regime metrics. Real ValidationReport accepts
those claims. The warmup default hides missing trailing evidence beyond warmup;
zero and boolean observations are not valid market prices. Current normal
ValidationEngine backtests the same close series first and rejects those inputs,
so no affected production report, calibration or false graduate is established.

## Decision

After original window/calendar checks, existing inner alignment and the existing
matched strategy-return wealth guard, validate only a nonempty matched market.
Require real nonboolean numeric dtype via the established pandas numeric/bool/
complex predicates. Refuse missing, nonfinite or nonpositive matched prices using
native Series checks, without narrowing to Float64, filling, dropping or repair.
Raise ValueError before pct_change or regime scoring. Object dtype, including
Decimal/numeric-string containers, is intentionally unsupported; arbitrary
coercibility is not numeric evidence. An empty matched market retains the prior
empty result regardless of its dtype. Unmatched invalid numeric values remain
unscored; object dtype remains unsupported even when its matched leaves happen
to be numeric.

Preserve original window/calendar/wealth-check precedence, inner alignment,
default20, valid zero horizons, genuine warmup-bull behavior, grouping, products,
Sharpe, report schema and every numerical operation for accepted prices. Native
finite extended precision is not subjected to a binary64 finiteness projection.
Derived trailing-return overflow and arbitrary huge pandas horizons remain
separate; this is a source-price contract, not arithmetic recovery, market
provenance, cadence, switching-account or complete-source certification.

No selector, threshold, gate/search identity, accounting-v14, generated record,
calibration or frozen-cohort change. Source provenance hashes change only for
the edited helper; current production inputs already satisfy the contract.

## Options considered

1. Guard the nonempty matched market with established dtype/value checks.
   Chosen: narrow descriptive-evidence boundary, preserving unscored rows.
2. Validate every original market value before alignment.
   Rejected: broader source-completeness policy than the scored intersection.
3. Replace undefined trailing observations with a new unknown regime.
   Rejected: invents a new partition policy and still accepts invalid prices.
4. Coerce object containers or fill missing prices.
   Rejected: repairs or reinterprets malformed evidence instead of refusing it.
5. Rely on the normal backtest boundary.
   Rejected: leaves the independently public regime helper issuing finite claims.

## Verification and reversal

Observe RED before runtime edits for the three actual report witnesses, invalid
prices at matched first/interior/last rows, nonfinite/nonpositive native and
nullable evidence, unsupported dtype families and refusal before pct_change.
Keep empty/disjoint/partial alignment, unmatched-invalid numeric values,
window/calendar/wealth precedence, valid numeric/nullable/extended inputs, zero
horizons and source immutability controls. Hypothesis covers invalid matched
observations and exactly-once valid-price partition accounting.

Twenty-four valid pre-edit payloads are frozen in
/tmp/qf-w43-s3-regime-market-baseline.json, SHA256
b97102e4d71997b78a67f340f97b8b7aeecad76103cb270c21dc7bc830485253.
Compare exact payloads and the complete prior AST after removing only new
imports/guard and restoring the leading helper docstring. Independent final
research review and foreground make check-all precede explicit-path commit,
fresh fetch/rebase, individual HEAD:master push and exact CI verification.

Reversal removes only the matched-market guard/imports and restores its prior
docstring, reopening FINDING-273. Preserve the written evidence if reversing.
