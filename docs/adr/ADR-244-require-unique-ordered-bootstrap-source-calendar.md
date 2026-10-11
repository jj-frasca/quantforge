# ADR-244: Require a unique ordered bootstrap source calendar

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 33, ISO 2026-W41
- **Resolves:** FINDING-193
- **Extends:** ADR-036, ADR-037
- **Relates to:** ADR-176, ADR-231

## Context

The bootstrap null resamples adjacent close returns with their source bar's
OHLCV geometry. Duplicate index labels expand source.loc[returns.index], so
the sampled return and geometry no longer refer to the same bar. Unordered
calendars also define adjacency in a different order than their observation
identity. A synthetic four-row source reproduced the mismatched pairing;
this does not establish corrupt production sources or revised null rates.

## Options Considered

1. Refuse duplicate or unordered source indexes before return calculation.
   This preserves evidence and the existing null law, but rejects malformed
   direct callers that previously produced a frame.
2. Sort or deduplicate. Convenient, but chooses or changes original observations
   and hides the source defect.
3. Align only by position. Prevents label expansion, but still accepts an
   ambiguous or chronologically reordered source calendar.

## Decision

After the existing n_bars refusal and before pct_change, filtering or RNG,
require source.index.is_unique and source.index.is_monotonic_increasing.
Raise ValueError on malformed calendars. Do not sort, deduplicate, reindex,
require DatetimeIndex/UTC/daily cadence, or change valid native source arithmetic.

Preserve ordered generic, naive, aware and irregular calendars; empty/singleton
sources retain the existing no-returns refusal. No new price, geometry, scalar,
completeness or generator-domain policy is introduced. The same seed, draws,
returns and OHLCV pairing on valid inputs remain exact. No threshold, search,
fingerprint, workflow, source acquisition or generated record changes.

## Verification and reversal

Observe duplicate/reordered-source failures first. Verify exact native seeded
OHLCV construction, caller nonmutation, short/empty/parameter precedence and
Hypothesis nonidentity permutations. Independently review and run the full
foreground gate before delivery. Removing the predicates reopens FINDING-193.
