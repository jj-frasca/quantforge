# FINDING-061: The bars cache-aside "miss" check ignores the requested date range

- **Severity:** Medium-High
- **Status:** **Fixed**, session 116 (2026-09-26). `scripts/peer_check.sh` showed
  `backtest.py`/`monte_carlo.py`'s last peer touch was 2026-09-23 (3 days cold, no
  uncommitted peer changes there) and `validation.py` cold since 2026-06-04 — territory was
  free. Fixed per the "Suggested fix direction" below: `_load_frame` (`backend/app/api/v1/
  backtest.py`) now checks range coverage via a new `_covers_range` helper (first/last
  cached bar within a 5-calendar-day tolerance of the requested `start`/`end`, to allow for
  weekend/holiday gaps) in addition to the existing bar-count floor. `monte_carlo.py` gets
  the fix for free (imports `_load_frame`). `validation.py`'s inlined duplicate copy was
  consolidated to call the shared `_load_frame` instead of re-implementing the same logic —
  matching `monte_carlo.py`'s existing pattern and closing the "fixing the logic twice" risk
  this finding flagged. See `fix(api): check cached range coverage, not just bar count` for
  the commit. The Backtest/Validation Sharpe-divergence question below was a **separate
  thread, now resolved (session 117, 2026-09-26, see below): not a bug** — `/validate`
  deliberately runs its own catalog-derived grid search (ADR-010), never the Backtest Results
  page's specific config, so the two numbers were never expected to agree.
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

### Resolution of the Sharpe-divergence thread (session 117, 2026-09-26): not a bug — the two pages run different experiments by design

Read `/validate`'s implementation (`backend/app/api/v1/validation.py`) and
`grid_from_catalog` (`backend/app/research/strategies/grid_generator.py`) directly rather than
speculating from the observed numbers. `/validate` never runs the request's implicit "Backtest
Results config" at all — per **ADR-010** (`docs/adr/ADR-010-strategy-catalog.md` §Consequences,
"`/validate` is now catalog-driven too"), it mechanically derives its own grid from the catalog's
`[minimum, maximum]` bounds (`n_per_param=3`) and reports `observed_sharpe` as
`sharpes[argmax(sharpes)]` (`app/validation/engine.py:166-167`) — the BEST of that grid, not any
specific hand-picked config. Ran `grid_from_catalog(find_catalog_entry("sma"), n_per_param=3)`
directly to see exactly what grid "sma" produces:

```
(fast, slow) = (1, 2), (1, 251), (1, 500), (100, 251), (100, 500), (200, 251), (200, 500)
```

**None of these 7 configs is anywhere near Backtest Results' own default (fast=20, slow=50)** —
by construction, since `n_per_param=3` linspaces the FULL catalog bounds (fast: 1-200, slow:
2-500) rather than sampling near the default. So Validation Report's Observed Sharpe for "sma"
can never equal, and has no reason to resemble, the Backtest Results page's own -0.76 for
fast=20/slow=50 — **this is true independent of the truncation bug this finding fixes**, and
would have been true even before the fix. The `0.00`/`0.0%`-everywhere reading specifically is
also fully consistent with this: several of the 7 grid points are extreme (fast=1 or slow=500 on
what was, at the time, a 251-bar truncated frame) and quite plausibly produced degenerate
(flat/no-trade) equity curves that argmax then picked among.

**Verdict: not a bug.** ADR-010 deliberately made `/validate` search the strategy's whole
parameter space (to measure the SELECTION procedure's overfitting risk via PBO/CSCV) rather than
validate one hand-picked config — that is the entire point of the feature, and the ADR's own
rationale reads as an intentional, reasoned tradeoff, not an oversight. The one genuine gap this
resolution surfaces is a **UI-honesty gap, not a logic bug**: `ValidationReportView.tsx`'s
"Observed Sharpe" tooltip never tells a reader this number comes from the catalog's own grid
search rather than whatever config is shown on Backtest Results — every other metric on this
page's Term tooltips (e.g. the walk-forward Sharpe's "measures the selection procedure rather
than one hand-picked config") already carries exactly this kind of disambiguation, so this one
is the odd one out. See the follow-up commit for that fix.

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

**Verified (session 117, 2026-09-26): the pipeline assumption above understates it.** Every
`backend/scripts/*.py` entry point (`hunt.py`, `run_hunt.py`, `shard_hunt.py`,
`cross_sectional_hunt.py`, `cross_sectional_forward.py`, `consolidate_pool.py`, `paper.py`,
`paper_broker.py`, `fundamental_sweep.py`, `null_calibration.py`, `prepare_panel_null.py`,
`window_experiment.py`, `history_length_experiment.py` — grepped the whole directory, not a
sample) calls `adapter.fetch_price_bars(symbol, start, now)` **directly**, never
`PriceBarRepository.get_bars` / `_load_frame` / `DataIngestionPipeline`. `grep -rln "get_bars\|
DataIngestionPipeline" app/research/` returns nothing either. So the pipeline isn't "affected in
practice because it happens to always request the full range" — it structurally never touches
the cache-aside code path this finding describes at all; it re-fetches from the adapter fresh on
every run, every script, unconditionally. **This bug class cannot occur in the research
pipeline, full stop** — the entire blast radius was, and is, the API layer
(`backtest.py`/`validation.py`/`monte_carlo.py`) and whatever calls it (the frontend, or any
future direct API client).

## Fix (implemented session 116, 2026-09-26)

Exactly as suggested below: `_load_frame`'s miss condition is now
`len(bars) < _MIN_BARS or not _covers_range(bars, start, end)`, where `_covers_range` checks
`bars[0].timestamp_utc - start <= 5 days` and `end - bars[-1].timestamp_utc <= 5 days` (empty
`bars` is always a miss). The 5-day tolerance is the longest realistic NYSE closure (a holiday
landing next to a weekend); it deliberately does not demand an exact boundary bar, since trading
calendars have gaps. Relies on the same overlap-safe `save_bars` upsert semantics named below —
re-ingesting a widened range is safe. `validation.py`'s inlined duplicate was replaced with a call
to the shared `_load_frame`, so there is now exactly one implementation of this logic, matching
how `monte_carlo.py` already consumed it.

Regression coverage: `test_backtest_endpoint_widens_a_narrower_cached_range` and
`test_validate_endpoint_widens_a_narrower_cached_range` reproduce this finding's exact scenario
(pre-warm with a narrower in-window slice, request the wider range, assert the full range is
actually served); `test_backtest_endpoint_true_cache_hit_does_not_call_adapter` guards against
overcorrecting into "always re-ingest" by asserting a genuine full-coverage hit still skips the
network fetch.

## Original suggested fix direction (superseded by the "Fix" section above)

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
