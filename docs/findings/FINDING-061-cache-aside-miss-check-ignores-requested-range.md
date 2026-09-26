# FINDING-061: The bars cache-aside "miss" check ignores the requested date range

- **Severity:** Medium-High
- **Status:** Open — reproduced and root-caused, **not fixed this session**. Every file that
  would need to change (`backend/app/api/v1/backtest.py`, `validation.py`, `monte_carlo.py`) is
  currently peer-hot (all three carry a same-day peer commit as of 2026-09-23, confirmed via
  `git log -3` before writing this up) — per `AUTONOMY_CHARTER.md`'s peer-collision rules, this
  session read and root-caused the bug but left the fix for whoever next has that territory free
  (the peer itself, or a future session once `scripts/peer_check.sh` shows it's gone cold).
- **Found:** 2026-09-26, autonomous session 115, live-driving Backtest Results + Validation
  Report against the real running dev servers with real yfinance data (the same "agent eyes"
  technique that found FINDING-060/ADR-131/ADR-130 in prior sessions).
- **Affects:** `_load_frame` in `backend/app/api/v1/backtest.py` (shared by `monte_carlo.py` via
  import) and the near-identical inlined copy in `validation.py`. All three read:
  ```python
  bars = repository.get_bars(symbol, start, end)
  if len(bars) < _MIN_BARS:      # _MIN_BARS = 30
      DataIngestionPipeline(adapter, repository).ingest(symbol, start, end)
      bars = repository.get_bars(symbol, start, end)
  ```

## Finding

The cache-aside "hit" condition is **"did the repository return at least 30 bars for this
symbol within the requested window,"** not **"does the repository's data actually cover the
requested `[start, end)` range."** `InMemoryPriceBarRepository.get_bars` correctly filters to
bars inside `[start, end)`, so it never returns bars *outside* the request — but it silently
returns however many bars *happen to already be stored* inside that window, which can be far
fewer than the window actually contains if an earlier, narrower ingest only ever populated part
of it. **Confirmed the real `TimescaleDB` repository shares this exact shape**
(`backend/app/data/storage/timescale.py::get_bars`, read directly this session): the same
`WHERE timestamp_utc >= start AND timestamp_utc < end` SQL filter, no row-count-vs-range check
either. Both `PriceBarRepository` Protocol implementations are affected identically — this is
not a memory-backend-only dev quirk, it would reproduce against the production TimescaleDB store
too, since the bug lives entirely in the shared endpoint code that calls either repository, not
in a repository-specific quirk.

**Reproduced end-to-end this session:**
1. Data Explorer: ingested AAPL for `2025-09-26 .. 2026-09-26` (the page's own default 1-year
   range) → 251 bars stored.
2. Backtest Results: ran the page's own default AAPL SMA-crossover config, whose default date
   range is `2021-09-26 .. 2026-09-26` (5 years) — a strictly WIDER window that fully contains
   the one already cached.
3. Result: **"Total return -18.2% over 251 bars"** — the backtest silently ran on the same 1
   year of data from step 1, not the requested 5 years. `len(bars)` was 251, comfortably above
   `_MIN_BARS = 30`, so the miss branch never fired and the other ~4 years were never fetched.
4. No error, warning, or indication anywhere in the UI or API response that the actual date
   range served was narrower than requested — a user (or, here, a research pipeline) has no way
   to detect the truncation short of independently computing the expected bar count for the
   window and comparing.

A secondary, less certain observation from the same session: the Validation Report run
immediately after (same symbol, same nominal 5-year range, "sma" strategy) showed **Observed
Sharpe 0.00** and a Regime Breakdown with **0.0% total return in both Bear and Bull buckets** —
starkly different from the Backtest page's own -0.76/-18.2% for what a user would reasonably
expect to be the same config. This session did **not** fully separate how much of that
divergence is caused by this same truncation (validation.py has its own independent
`repository.get_bars` call, so it might genuinely re-derive a different 251-bar window depending
on exactly how caching left the store) versus a different, unrelated default-parameter mismatch
between the two pages' notion of "SMA Crossover" (Backtest Results' own default is fast=20/
slow=50; the catalog's own preset text elsewhere on the same page says "SMA(50 / 200)" for the
"SMA crossover on SPY" example, suggesting the catalog's canonical default may differ from the
page's pre-filled form default) — flagging this as a real but **not yet disentangled** second
thread, not asserting it as the same bug.

## Why this matters

This is exactly the class of bug CLAUDE.md rule 6 and the frontend "Honesty in UI" convention
exist to prevent — data silently narrower than requested, with a confident-looking result and no
flag. It is invisible to the existing test suite because every backend test presumably ingests
fresh into an empty repository or an already-correctly-ranged one; it only manifests when a
**prior, narrower ingest for the same symbol already happened** in the same repository instance
— exactly what an interactive multi-page user session does (ingest to explore, then backtest a
wider window), and exactly what this session's own live-browser "agent eyes" pass was designed
to catch (per RUNNING_STATE.md session 106/114's own retros: bugs that only manifest from real,
stateful interaction, not a single mocked unit test).

Real-world blast radius is probably concentrated in the **interactive frontend flows** (a real
user, across sequential requests, ingesting a narrow range then later requesting a wider one —
now confirmed to reproduce identically against either repository implementation) rather than the
autonomous research pipelines (`hunt.py`, `daily_discovery`, etc.), which — as far as this
session checked without reading their full call graphs — likely always ingest their own full
needed range in one shot per symbol rather than incrementally widening an existing cache entry.
That pipeline assumption is **not verified this session** and should be checked by whoever picks
this up.

## Suggested fix direction (not implemented — peer territory)

The miss condition needs to check **range coverage**, not just count: e.g. compare the earliest/
latest cached `timestamp_utc` against the requested `start`/`end` (or have
`DataIngestionPipeline.ingest` be idempotent-safe to call unconditionally on a widened range,
relying on `save_bars`' existing upsert-by-`(timestamp_utc, source)` semantics — already
overlap-safe per the comment in `InMemoryPriceBarRepository.save_bars` — so the fix could be as
narrow as "always ingest if the cached range's min/max don't cover `[start, end)`," not a full
rewrite of the caching strategy). Three call sites need the same fix
(`backtest.py::_load_frame`, `validation.py`'s inlined copy, and `monte_carlo.py` gets it for
free via `_load_frame` once that's fixed) — consider consolidating `validation.py`'s copy to call
the shared `_load_frame` helper while fixing this, rather than fixing the logic twice.
