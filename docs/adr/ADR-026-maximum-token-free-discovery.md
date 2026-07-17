# ADR-026: Maximum token-free discovery via sharded parallel daily hunts

- **Status**: Accepted
- **Date**: 2026-07-17
- **Deciders**: Joe Frasca
- **Extends**: ADR-014 (research harness), ADR-015/016 (gate + MinTRL), ADR-018 (universe deflation), ADR-024 (cross-sectional)

## Context
Discovery in QuantForge is **token-free**: the hunt is pure Python (vectorized pandas/numpy
backtesting + the deterministic gate), no LLM in the loop. The repository is **public**, so GitHub
Actions minutes are **effectively unlimited**. Yet today discovery runs only **weekly** (Sunday) over
a **static 503-name S&P universe** — a tiny fraction of what the free compute allows.

The instinct to "search less so we don't overfit" is misplaced here: the graduation gate is
**self-penalizing**. Per-symbol trial counts feed the Deflated Sharpe and MinTRL bar (ADR-015/016),
and universe-level deflation scales the required holdout Sharpe with the number of names searched
(ADR-018). **More searching RAISES the bar it must clear — it cannot manufacture false graduates.**
So the honest move is to search as much as makes sense and let the gate reject the noise.

## Decision
Run discovery **daily at maximum breadth** via a **sharded matrix workflow**, token-free.

### Sharding + parallelism
- The universe is split into **N shards**; each shard is a **parallel Actions job** running the full
  strategy catalog hunt on its slice (`scripts/hunt.py <shard-symbols>`).
- Each shard writes its experiments to its **own** output (a per-shard JSON), uploaded as a workflow
  **artifact**. Shards never write the shared pool — this eliminates the N-parallel-jobs-committing-
  master race that a shared `research_pool.json` would create.
- A final **consolidation job** downloads every shard artifact, **merges** the experiments into
  `data/research_pool.json` (dedup by `experiment_id`), runs **promotion** into the managed paper
  book once, and commits once (rebase-retry).

### Coverage + rotation
- Shard assignment rotates by date so the whole universe is swept frequently and then **revisited**
  (a strategy that graduated once must keep clearing the gate on fresh data). Every day therefore
  explores **new tickers** and any **newly-added strategies** (the hunt always uses the current
  catalog).

### New horizons (universe expansion)
- Expand beyond the S&P: add **Russell-scale** large/mid-cap lists and **liquid ETFs** as additional
  universe files, so discovery reaches more of the market. yfinance is the source (long history);
  it rate-limits from cloud IPs, so shards stagger + retry + cache.

### Honesty (non-negotiable)
- Scaling discovery does **not** weaken rigor: DSR/PBO/MinTRL/holdout/beat-benchmark all still apply,
  and universe-level deflation (ADR-018) makes the bar rise with breadth. This ADR buys **more shots
  on goal**, each judged by the same unforgiving gate — not easier graduation.

## Options Considered
- **Keep the weekly single-job hunt.** Rejected: leaves almost all the free compute idle and can't
  deliver daily discovery over a broad, rotating universe.
- **One daily job over the full universe.** Rejected: a full universe x catalog x coarse-to-fine
  sweep won't finish inside the 6h job cap as the universe grows; parallel shards scale horizontally.
- **Parallel shards each committing the pool directly.** Rejected: N jobs racing to commit
  `research_pool.json` to master is a rebase storm. Artifacts + a single consolidation commit is clean.
- **Lower the gate to graduate more.** Rejected outright — that's the one thing we never do. Breadth
  is honest; a looser gate is not.

## Consequences
- A genuinely industrial discovery loop: thousands of (symbol x strategy x config) trials per day,
  token-free, all funnelled through the same gate. Expect **very few** graduates — that's the point.
- New obligation: a pool-consolidation/merge component (dedup, idempotent) and the matrix workflow;
  the JSON pool is the near-term store (a Timescale/DB-backed pool is a later ADR once volume demands).
- Watch items: yfinance cloud rate limits (stagger/retry/cache), Actions concurrency limits (cap the
  matrix width), and pool file size growth (consolidation prunes/rolls if needed, a later concern).

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
