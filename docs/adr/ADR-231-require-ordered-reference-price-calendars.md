# ADR-231: Require unique ascending reference price calendars

- **Status:** Accepted
- **Date:** 2026-10-09
- **Deciders:** Codex autonomous session 22, ISO 2026-W41
- **Resolves:** FINDING-181
- **Extends:** ADR-176, ADR-223, ADR-230

## Context

Reference returns and AR predictions use positional adjacent rows. Valid positive
prices with an unordered calendar can therefore use a later dated return as the
preceding observation for an earlier prediction. Duplicate rows also lack a
unique observation identity. ADR-176 already enforces this intrinsic ordering
contract in the backtest engine, but reference scoring does not inherit it.

## Options Considered

1. Reject unordered/duplicate source indexes before return calculation. This
   preserves evidence and makes positional adjacency consistent with index
   ordering; malformed direct callers now fail explicitly.
2. Sort or deduplicate sources. Convenient but changes the evidence order or
   chooses among competing observations, concealing caller defects; rejected.
3. Trust generator calendars. Avoids another guard but leaves public reference
   calls able to publish scores on malformed frames; rejected.

## Decision

The shared _reference_returns boundary requires a unique monotonically increasing
price index before pct_change and short-history shortcuts, matching ADR-176.
All three scorer entries inherit this guard before forming returns or AR lags.
Retain ordered generic indexes, naive and aware calendars, empty and singleton
histories. Do not sort/deduplicate, require UTC/DatetimeIndex, enforce daily cadence
or alter the conditional-mean reindex/missing-startup semantics.

Preserve valid native scores, sign/lag/turnover/cost conventions, reference
methods/defaults, search/gate thresholds/fingerprints and generated records.
The guard establishes source index ordering, not arbitrary prediction causality,
acquisition lineage or correctly spaced daily observations.

## Verification

Observe failing generic/historical/explicit-AR tests before adding the guard.
Reject reordered and duplicate datetime/integer calendars, including short
histories. Protect exact gross/net answers on all supported ordered indexes.
Include a Hypothesis property rejecting nonidentity row permutations of unique
ordered prices. Independent review and full foreground make check-all precede
explicit-path commit, fresh sync, individual push and exact master CI watch.

## Consequences and reversal

Malformed source geometry cannot produce a reference effect-size claim. Caller
calendar repairs must be explicit outside scoring. No historical corrupt artifact
or revised power count is inferred. Remove the two index predicates to reverse
this decision, reopening FINDING-181.
