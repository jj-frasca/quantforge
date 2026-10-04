# ADR-170: Anchor paper benchmarks to completed daily closes

- **Status:** Accepted
- **Date:** 2026-10-04
- **Deciders:** Codex autonomous session 28
- **Resolves:** FINDING-101
- **Extends:** ADR-006, ADR-021, ADR-141, ADR-169

## Context

Fetching SPY from the first account snapshot excludes a preceding completed daily close under
the adapter's half-open timestamp contract. This can drop the first benchmark movement. A daily
bar's midnight label also does not establish that its close was available at a snapshot instant.

## Options Considered

1. Fetch a bounded lookback and require completed regular-session close anchors at both endpoints.
   This corrects the scheduled after-hours proxy while declining ambiguous observations.
2. Fetch exact intraday marks. This requires new acquisition and valuation semantics beyond this fix.
3. Shift the fetch start alone. This still permits an unfinished endpoint or silently stale anchor.

## Decision

Extract a network-injectable helper, using the existing adapter and checked ResearchDataset path.
Fetch from New York midnight fourteen calendar days before inception. Interpret daily bars only
when their labels are New York midnight. For weekday snapshots before 09:30 use the preceding
weekday close; at or after 16:00 use that day's close; on weekends use Friday. Decline regular-hour
snapshots. Require the exact expected date at each endpoint: missing bars (including holidays),
quality failures, unsupported labels, and fetch failures leave benchmark and alpha unmeasured.

This is explicitly a completed regular daily-close proxy, not exact intraday account attribution.
Early-close days remain conservatively unavailable until 16:00; the weekday calendar deliberately
declines cases that need holiday knowledge rather than silently using an older close. Do not rewrite
historical snapshots or change nominal/inception account formulas. A first snapshot has no measured
benchmark. Same-close endpoints legitimately yield zero.

Require the derived float return to be finite and strictly greater than -1; overflow and rounded
complete-loss ratios from finite positive closes remain unmeasured. An intraday first observation
leaves future proxy alpha unmeasured because its baseline cannot be established by daily closes.

## Evidence and consequences

The offline half-open adapter example 100 → 110 → 121 yields 21% from the inception close; the old
fetch produces 10%. Regression tests cover endpoint availability, weekends, DST, missing anchors,
quality rejection, and financial ratio invariants. This does not verify any historical live fetch.

Alpaca documents New York day labels and excludes extended-hours trades from daily close updates:
[market-data FAQ](https://docs.alpaca.markets/us/docs/market-data-faq). The regular-session convention
uses [NYSE core hours](https://www.nyse.com/trade/trading-information). Late vendor corrections and
the account's use of after-hours marks remain limitations of this reporting proxy.

## Reversal

Restore the inline first/last-bar ratio. This reopens FINDING-101 and is not recommended.
