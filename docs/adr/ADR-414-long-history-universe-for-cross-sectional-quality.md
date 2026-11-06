# ADR-414: A long-history universe for cross-sectional quality/value search

- **Status:** Accepted
- **Date:** 2026-11-06
- **Deciders:** Interactive session (Joe present: "find credible alpha... you own this, make it
  happen")
- **Acts on:** FINDING-350
- **Relates to:** ADR-024 (cross-sectional engine), ADR-029 (fundamentals division),
  ADR-046/ADR-104 (lifetime-trial DSR/PBO denominator), `app/research/lab/history.py`'s
  `RECENT_HISTORY_START`/`SEARCH_HISTORY_START` split.

## Context

FINDING-350 measured that `xs_quality` wins the cross-sectional selection step 11/11 times it has
been eligible to compete, cleanly and by a wide margin (unlike the single-name technical search,
where ADR-060 found the selection step barely distinguishable from noise). It is blocked from
graduating only by DSR/MinTRL — the lifetime-trial-count selection penalty — and the best-measured
instance missed MinTRL's required track record by roughly a tenth of a year, not an order of
magnitude.

The panel's available in-sample history is capped by `RECENT_HISTORY_START` (2005-01-01) at
roughly 17.4 years (80% of a ~21.75-year span, after `split_panel_holdout`'s default 20%
holdout). `RECENT_HISTORY_START`'s own comment in `history.py` states the reason: "the cross-
sectional hunt... whose panel is bounded by its newest member, so older bars per symbol buy it
nothing." That is correct for `data/universes/large_cap.txt` (the 51-symbol universe actually
used) as assembled — checked directly this session, not assumed: 14 of its 51 symbols
(`NVDA, GOOGL, AMZN, META, TSLA, CRM, QCOM, AVGO, V, MA, GS, MS, ABBV, NFLX`) have no price history
before the 2000s, and they are what forces the panel's common start to 2005.

`RECENT_HISTORY_START` cannot be moved — it is shared by the paper book, broker, cross-sectional
forward scoring, and consolidation's position management (`history.py`'s own docstring), and
moving it would be an unreviewed, out-of-scope change to code this ADR has no business touching.
What CAN move, without touching that constant or any gate/threshold, is *which symbols* the
cross-sectional hunt is pointed at.

## Decision

**Ship a new, static, verified universe file — `data/universes/large_cap_longhistory.txt` — built
from symbols independently confirmed (live yfinance query, this session) to have real price data
in Q1 1990, and let the existing `cross-sectional-hunt.yml` `workflow_dispatch` `universe` input
point at it.** No code changes. No new mechanism. `cross_sectional_hunt.py` already accepts any
universe file by path; `cross-sectional-hunt.yml` already exposes `universe` as a dispatch input
(it currently defaults to `large_cap.txt`). This ADR only adds a second committed universe file
and uses the dispatch mechanism that already exists for exactly this purpose.

**Verification method, stated precisely so it can be reproduced or challenged:** every symbol in
`data/universes/sp500.txt` (503 symbols) was queried for `fetch_price_bars` over 1990-01-02 to
1990-03-31. A symbol is included only if that three-month window returns at least 55 trading bars
— tight enough to exclude a symbol that IPO'd partway through the quarter (CSCO, IPO'd 1990-02-16,
returns 30 bars in this window and is excluded) while tolerant of the ordinary handful of missing/
adjusted bars real vendor data has. This is a data-availability check only; it makes no claim
about data quality beyond "a price exists," which `DataQualityEngine` (ADR's own existing
pipeline) still checks before any of this data reaches a strategy.

## What this is NOT

- **Not a change to `RECENT_HISTORY_START`, `SEARCH_HISTORY_START`, or any other shared constant.**
  Every other consumer of `RECENT_HISTORY_START` is unaffected.
- **Not a change to DSR, PBO, MinTRL, holdout, or any gate threshold.** The same unmodified gate
  judges whatever this universe produces.
- **Not a guarantee of a different result.** FINDING-350 was explicit that several of the 11
  historical `xs_quality` runs needed 28–32 years, which even a 1990-start panel (~28.8y in-sample
  at the current holdout split) may not clear. This ADR increases the evidence available to the
  search; it does not pre-determine what that evidence will show. A null result here (still
  doesn't graduate, even with more history) is itself a real, useful finding and must be reported
  as such, not quietly discarded.
- **Not a backfill or edit of any generated `data/*.json`.** `cross_sectional_pool.json` remains
  sole-written by the scheduled cloud workflow (ADR-030); this ADR ships a new *input* file only,
  then dispatches the existing workflow to let it write its own result the normal way.

## Alternatives considered

- **Lower `min_holdout_bars`/`holdout_fraction` to free up more in-sample years from the same
  2005-start panel.** Rejected: that changes the holdout's own statistical power, a gate-adjacent
  parameter, for every cross-sectional search, not just quality/value — exactly the kind of change
  this project's hard limits reserve for its own dedicated, evidence-backed ADR, not a side effect
  of a universe swap.
- **Move `RECENT_HISTORY_START` itself back to 1990.** Rejected for the reason stated in Context:
  it is shared by several other consumers whose own behavior this ADR has no mandate to change,
  and the existing comment's "bounded by its newest member" reasoning is correct for the general
  multi-decade-old-and-new mixed universe `large_cap.txt` represents.
- **Use the full S&P 500 (`sp500.txt`) filtered to 1990-qualifying members, rather than a separate
  curated file.** Considered and effectively adopted: the verification pass queried the full
  503-symbol file and kept every qualifying member (not a hand-picked subset), so this is in
  practice "the S&P 500, filtered," not a narrower hand-curated list. Shipped as its own file
  rather than a runtime filter so the exact universe is a committed, reviewable, reproducible
  artifact rather than something that silently changes if `sp500.txt` is ever edited.

## Consequences

- `data/universes/large_cap_longhistory.txt` ships as a new, static, git-tracked file. It is not
  touched by any scheduled workflow's writer path — it is an input, like `large_cap.txt`.
- The next step (this session, immediately following) dispatches `cross-sectional-hunt.yml` with
  this universe to get a real, gate-measured result. That result — whichever way it comes out —
  gets its own dated addendum to FINDING-350, not a new finding, so the full before/after chain
  stays in one place.
- If this universe graduates something, that graduate is subject to every existing downstream
  check (paper book promotion, forward scoring, the honest "beats buy-and-hold" accounting ADR-073
  fixed) exactly like any other graduate — nothing about its provenance exempts it from any later
  scrutiny.

## How to reverse

Delete `data/universes/large_cap_longhistory.txt`. No other file depends on its existence; the
default `cross-sectional-hunt.yml` dispatch input remains `large_cap.txt` and is unaffected.
