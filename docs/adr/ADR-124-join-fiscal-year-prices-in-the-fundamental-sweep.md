# ADR-124: Join fiscal-year prices in the fundamental sweep

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-052
- **Extends:** ADR-022, ADR-029 Layer 3

## Context

`fundamental_sweep.py` scores each company's `UndervaluationScore` from a single most-recent close,
never joining a price series onto `FundamentalsHistory`'s per-year `period_end`s via
`attach_fiscal_year_prices`. `compute_multiples`'s own-history P/E and P/S percentile legs require
each year's `price` to be populated to build a distribution to rank against — without the join, that
distribution is always empty, so those two of `UndervaluationScore`'s three components never fire in
production, silently reducing `value_score` to just the DCF margin-of-safety leg (or `None`) for
every company the sweep has ever scored.

## Options Considered

1. **Fetch a price series spanning the company's fiscal-year history and join it before scoring,
   inline in `fundamental_sweep.py`.** Replace `_latest_price` (single 14-day-window close) with
   `_price_series` (ascending `(date, close)` series from the earliest `period_end` to now) and
   `_join_prices` (calls `attach_fiscal_year_prices`, falls back to the old latest-close-only
   behavior when no year has a `period_end` to anchor on).
   - Pro: matches the correct, already-tested composition pattern `value_filter.py`'s
     `make_value_provider` uses; reuses the `history` the sweep already fetched, so no second EDGAR
     call is added (only the existing yfinance call's date range widens — `fetch_price_bars` is one
     HTTP request regardless of range).
   - Con: the network-glue function itself has no direct unit test, matching this file's existing
     convention (`_latest_price`/`_sic_description` were also untested network glue) — verified
     instead by strengthening `compute_fundamental_record`'s own test to prove the pure
     join-then-score composition is correct when actually given a fully-joined history.
2. **Reuse `make_value_provider` directly inside the sweep instead of reimplementing the fetch.**
   - Con: `make_value_provider`'s `history_provider` would re-fetch `FundamentalsHistory` from EDGAR
     a second time per symbol (the sweep already has `history` in hand from its own quality-leg
     fetch) — an extra EDGAR call per company the script's existing rate-limit budget
     (`_EDGAR_MIN_INTERVAL_S`, two calls per symbol) doesn't account for.
3. **Leave it as DCF-only and update the docs/docstring to describe reality instead of fixing the
   wiring.**
   - Con: the honest description of "what value_score means" should be the documented three-way
     blend actually computing, not a permanently degraded description of a wiring bug — the
     pure-function side of this is already correct and tested; only the sweep's own composition was
     wrong.

Chose option 1: smallest correct diff, reuses `history` already in hand, follows the codebase's own
established correct pattern.

## Decision

`fundamental_sweep.py` gains `_price_series` (ascending `(date, close)` from a given start date to
now, sorted defensively — `attach_fiscal_year_prices`/`asof_close` require ascending order and raise
otherwise, and this codebase's own convention (`bars_to_frame`, `InMemoryPriceBarRepository.
get_bars`) is to sort defensively rather than trust vendor return order) and `_join_prices` (derives
the series start from the earliest year with a `period_end`, joins via `attach_fiscal_year_prices`,
falls back to the old 14-day latest-close-only window when no year has a usable `period_end`).
`main()` calls `_join_prices` in place of `_latest_price` and passes the returned, price-joined
history into `compute_fundamental_record`.

`compute_fundamental_record`'s test suite gains
`test_compute_with_full_price_history_populates_pe_ps_percentiles`, proving the pure
join-then-score composition actually produces non-`None` P/E and P/S percentiles when given a
history with real per-year prices — the regression guard for this fix, since the sweep script itself
follows this codebase's convention of untested live-network glue.

## Consequences

- `value_score` written to `data/fundamentals_pool.json` by the next weekly sweep run will reflect
  the full documented three-way blend (own-history P/E percentile, own-history P/S percentile, DCF
  margin of safety) for any company with enough price/fundamentals history, not just the DCF leg.
- No change to EDGAR call volume (still 2 calls/symbol); the yfinance call's date range widens from
  14 days to the company's full fiscal history, but remains 1 call/symbol regardless of range.
- A company with no `period_end` on any fiscal year (rare — EDGAR's `companyfacts` almost always
  reports it) falls back to the pre-fix behavior exactly (DCF-only), not a crash or an error.

## Reversal

Revert `main()` to call `_latest_price` and remove `_price_series`/`_join_prices`. Not recommended —
reintroduces FINDING-052's silently-DCF-only value leg for every company the sweep scores.
