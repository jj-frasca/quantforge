# ADR-095: Capture each company's SEC SIC classification in the fundamental sweep

- **Status**: Accepted
- **Date**: 2026-09-22
- **Deciders**: Autonomous session #95 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-029 Layer 3 (the fundamental discovery sweep and `FundamentalRecord`)
- **Relates to**: ADR-094 (the within-symbol history-length experiment that just ruled out length as
  the driver of the 7,400-vs-9,247-bar cohort magnitude gap, and named "sector mix" as one of the
  unmeasured composition candidates that could explain it)

## Context

ADR-094 answered the length-vs-composition question the three-cohort calibration write-up left open:
truncating a symbol's own history to 7,400 bars does not move its drift-controlled walk-forward
excess (`+0.000 [-0.028, +0.011]`), so the gap between the 7,400-bar and 9,247-bar cohorts is a fact
about *which symbols* populate each cohort, not about how much history the search sees. That ADR
named the plausible composition drivers — survivorship, sector mix, size — and noted none of them
is measurable today: `data/fundamentals_pool.json` (`FundamentalRecord`, `app/research/fundamentals/
record.py`) carries quality/value/F-score/gross-profitability per company, sourced entirely from
EDGAR's `companyfacts` API, and nothing about industry classification or company size.

SEC EDGAR's **submissions** endpoint (`https://data.sec.gov/submissions/CIK{cik:010d}.json`) — a
different endpoint from the `companyfacts` one `SecEdgarFundamentalsSource` already calls, same
host, same free/no-key access, same `<=10 req/s` etiquette — returns each filer's `sic` and
`sicDescription` fields directly (verified live against CIK 0000320193 / AAPL this session:
`{"sic": "3571", "sicDescription": "Electronic Computers"}`). This is the standard SEC industry
classification (Standard Industrial Classification), coarser than GICS but free, already keyed by
the CIK this project already resolves, and sufficient to test a "sector mix explains the cohort gap"
hypothesis without a new vendor or paid data source.

## Decision

**Add best-effort SIC capture to the existing fundamental sweep, following the exact resilience
pattern `_latest_price` already uses for the value leg — a failure degrades the record, it never
crashes the shard.**

1. `SecEdgarFundamentalsSource.fetch_sic(symbol) -> str | None` (`app/data/sources/edgar.py`):
   resolves the CIK exactly as `fetch`/`fetch_history` do, calls the submissions endpoint, and
   returns `sicDescription` — or `None` if the response omits it (an ETF/shell filer might). Reuses
   the same injectable `_fetch_json` the existing tests already exercise without network.
2. `FundamentalRecord.sic_description: str | None = None` (`app/research/fundamentals/record.py`) —
   a new optional field, default `None` so every pre-ADR-095 row already in `data/
   fundamentals_pool.json` continues to validate unchanged (pydantic default, no migration).
3. `compute_fundamental_record` gains an optional `sic_description: str | None = None` parameter and
   attaches it to the record it builds. Pure — no network in this function, consistent with the
   module's existing "network lives in the script" boundary.
4. `scripts/fundamental_sweep.py` fetches it best-effort per symbol, mirroring `_latest_price`'s
   `try/except (ValueError, OSError) -> None` shape exactly, and passes it through. One extra HTTP
   call per company sweep is inside the existing `<=10 req/s` budget the sweep already rate-limits
   itself to (`_EDGAR_MIN_INTERVAL_S`); no new rate-limit accounting needed.
5. **No backfill, no local write.** `data/fundamentals_pool.json` is cloud-workflow-written only
   (ADR-030); this session ships the capability and lets `fundamental-sweep.yml`'s existing weekly
   schedule populate it over the sweep's normal multi-week cadence across the ~10.4k-filer universe,
   same as every other field that field has ever gained.

## Alternatives considered

- **yfinance's `Ticker.info['sector']`.** Rejected: a different, less reliable endpoint than the
  `history()` call this project already depends on (frequently rate-limited or missing fields per
  this project's own operational notes on yfinance flakiness, ADR-031), and it would add a second
  network round-trip per symbol to a source already carrying the sweep's price leg. EDGAR's
  submissions endpoint is the same host and etiquette the sweep already respects.
- **A static SIC-to-sector lookup table committed to the repo.** Rejected: requires sourcing and
  maintaining a mapping outside EDGAR, and does not update as filers reclassify; the live endpoint
  is definitionally current and no harder to call than the one already in use.
- **Fetch SIC inside `fetch_history`/`fetch` instead of a separate method.** Rejected: it is a
  different endpoint returning unrelated data (entity classification vs. financial facts), and the
  existing methods' tests and call sites should not need to change shape to carry an unrelated field.
  A separate method keeps each fetch's failure mode independent, exactly as `_latest_price` is kept
  independent of the EDGAR facts fetch today.
- **Do this analysis now with yfinance instead of shipping sweep infrastructure.** Considered:
  `Ticker.info` could answer the sector question for the ADR-094 sample directly and immediately.
  Rejected in favor of the sweep-infrastructure route because the fundamentals pool is the project's
  system-of-record for company metadata (ADR-029), already covers the full universe on a schedule,
  and a one-off local pull would not persist for any future session to reuse — exactly the kind of
  generated-state discipline ADR-030 exists to enforce.

## Consequences

- `data/fundamentals_pool.json` rows gain `sic_description` as the sweep naturally revisits each
  company (multi-week cadence, ADR-029). No existing row changes until its company is next swept.
- Enables, but does not itself perform, a future test of ADR-094's remaining open question: whether
  sector mix (via SIC) explains the 7,400-vs-9,247-bar cohort composition gap. That analysis needs
  enough of the ADR-094 sample's SIC codes populated to be worth reading, which depends on the
  sweep's own schedule — not something this session can force without becoming a second writer.
- No change to any gate, threshold, or production search path. Purely additive metadata.

## How to reverse

Remove `sic_description` from `FundamentalRecord`, the parameter from `compute_fundamental_record`,
`fetch_sic` from `SecEdgarFundamentalsSource`, and the sweep's call site. Existing pool rows keep
working either way (the field defaults to `None` and pydantic ignores unknown keys on load in
neither direction — removing a field a stored row carries is a no-op for `model_validate`).

## Measured

Not applicable — this ADR ships sweep capability; it does not run an analysis. See ADR-094 for the
measurement this capability is meant to eventually support.
