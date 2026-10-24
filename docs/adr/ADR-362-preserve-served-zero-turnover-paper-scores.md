# ADR-362: Preserve served paper scores despite zero turnover

- **Status:** Accepted
- **Date:** 2026-10-24
- **Deciders:** Codex autonomous session 29, ISO 2026-W43
- **Extends:** ADR-073, ADR-361
- **Resolves:** FINDING-302

## Context

ADR-361 corrects the backend's zero-turnover inference. The paper table still
unconditionally hides served strategy Sharpe/return and comparison styling when
forward_trades is zero, including nonzero inherited-exposure scores. Its schema
comment repeats the same unsupported inference. Legacy default-zero counts do
not establish a historical absence of exposure or turnover.

## Options Considered

1. **Recognize affirmative evidence already served to the table.**
   - Pro: preserves scalar/curve evidence and server verdicts without API changes.
   - Con: zero scalars and missing/unit curves cannot distinguish inactivity,
     unavailable evidence or rounding; the text must acknowledge this limit.
2. **Always display every zero-count score numerically.**
   - Pro: simple, never hides supplied scalars.
   - Con: reintroduces ADR-073's apparent measured zero on inactive paths.
3. **Add new backend exposure/provenance fields.**
   - Pro: could provide more precise attribution for future records.
   - Con: expands durable contracts and cannot reconstruct missing legacy evidence.

## Decision

On positive-bar, zero-count rows, suppress strategy metrics only when both
served strategy scalars equal zero and every served strategy-equity point equals
unit wealth. Empty curves supply no affirmative curve evidence. Any nonzero
strategy return/Sharpe or any nonunit strategy-equity point preserves the served
numeric cells and authoritative beats/lag styling. Inspect every point, including
round trips and initial post-freeze movement; do not use an epsilon or benchmark
movement as strategy evidence. Do not recompute any score or verdict.

For suppressed rows say "no nonzero forward evidence recorded", followed by
"0 forward turnover events" and the supplied bar count. Measured zero-count rows
also show their zero turnover count. Qualify that legacy default-zero counts do
not attest historical execution. Preserve closed exit reasons, null scores,
nonzero-count behavior, formatting, API/schema expressions and all backend code.
Correct the stale schema comment only. This is visible-evidence classification,
not reconstruction of original returns, exposure, provenance or account entry.

## Consequences and reversal

The dashboard can display ADR-361 scores honestly while genuinely inactive/absent
evidence stays distinct from a measured zero. Some tiny nonzero values still
round to the existing numeric format; classification uses the supplied values.
Zero-return/rounded/missing evidence remains ambiguous. Add actual failing RTL
tests before implementation, preserve existing cases and cover scalar-only,
legacy empty curves, nonunit/round-trip curves, signed/tiny zeros, benchmark-only
movement, server flags and singular grammar. Required independent frontend
review, full foreground gates and exact master CI precede completion.

Reversal restores the trade-count-only presentation and reopens FINDING-302.
