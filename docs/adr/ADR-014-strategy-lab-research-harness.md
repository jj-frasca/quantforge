# ADR-014: StrategyLab — an agentic research harness that discovers validated strategies

- **Status**: Accepted
- **Date**: 2026-07-01
- **Deciders**: Joe Frasca

## Context
QuantForge has, as of ADR-013, a complete deterministic research stack: 11 catalog
strategies, a vectorized backtester, a benchmark comparator, a (still-dead) Monte Carlo
simulator, an `ExperimentManifest` reproducibility record, a catalog-driven
`grid_from_catalog` candidate generator, and a validation engine (PBO / Deflated Sharpe /
purged CV / walk-forward / parameter stability / regime analysis).

The new goal (Joe, 2026-07-01): stop hand-driving one backtest at a time and instead let an
**AI agent search the strategy + parameter space for a genuinely profitable strategy**,
persist its findings so future agents build on them, and eventually forward/paper-trade the
survivors. The identity stays **rigor-first** — this is not a pivot to a naive "AI picks
stocks" product. Paper trading is deferred until the search demonstrably produces
holdout-validated winners (substrate TBD in a later ADR).

This raises the defining question of the whole project: **how does a stochastic LLM agent
make correct, deterministic, reproducible decisions about money?** A naive
"loop: propose config → backtest → keep high Sharpe" is a multiple-comparisons machine —
the maximum Sharpe over N random strategies rises with N regardless of skill, so it
manufactures confident false positives. The antidote already exists in this repo (PBO,
Deflated Sharpe, purged CV); the harness must be built *around* it, not bolted on after.

## Decision

**Core principle: the LLM proposes and explains; deterministic tested code computes and
judges; a hard gate the model cannot override decides what graduates.** The agent never
produces a number or a verdict — only hypotheses and narration grounded in tool outputs.

Three layers:

### 1. Act — an MCP tool surface over the existing tested engine
Expose the research capabilities as MCP tools (thin wrappers over the already-tested
services/endpoints), so any agent — an interactive session, a fork, or a scheduled cron —
drives the same auditable, replayable verbs:
`propose_candidates`, `backtest`, `validate`, `benchmark`, `monte_carlo`,
`fundamentals`, `record_finding`, `query_pool`.
Tools return structured, schema-validated results; the agent composes them but computes
nothing itself.

### 2. Remember — an immutable, trial-counted research pool
Every experiment is written to a structured, queryable store as an
`ExperimentManifest` + the **full set of trials** (not just the winner) + the validation
report + the locked-holdout result + the agent's rationale. Two jobs:
- **Continuity**: future agents `query_pool` before searching, so we build on prior
  findings instead of re-searching (and re-overfitting) from scratch.
- **Honesty flywheel**: the pool is the authoritative count of *how many strategies have
  ever been tried* on a symbol/universe. That count feeds the **Deflated Sharpe trial
  penalty** — the more we hunt, the higher the bar to clear. Overfitting is priced in.

Storage starts **structured** (a DB/JSON experiment store keyed by manifest hash);
vector/embedding search over rationales is a **later addition**, added only when the pool
is large enough to need semantic recall (no premature RAG — see
[[feedback-evidence-based-changes]]).

### 3. Judge — a deterministic gate + a locked out-of-sample holdout
A candidate graduates **iff** it passes coded thresholds, not an LLM judgment:
- A fixed **out-of-sample holdout** (default: the most recent ~18 months) is split off
  **before any search begins** and is never passed to any search-time tool. It is read
  exactly once, when a finalist is scored. It is the only number to be trusted.
- Graduation predicate (config, tunable, versioned): `deflated_sharpe > 0` **and**
  `pbo < 0.5` **and** walk-forward mean Sharpe > 0 **and** the holdout Sharpe stays
  positive and within a tolerance band of the in-sample estimate. Monte Carlo P(ruin)
  and the benchmark IR are risk gates layered on top.
- The gate lives in tested code. The agent may *rank* survivors and *explain* them; it
  **cannot** promote a strategy the gate rejects.

### Fundamentals & sentiment (new data layer, citation-backed)
A `FundamentalsSource` (P/E, revenue growth, margins, general outlook, sentiment) parallel
to the price `DataSourceAdapter`, cached with a **freshness TTL** and refreshed often. Used
as (a) a universe filter ("sane fundamentals only") and (b) features. Every figure carries a
source + as-of date; copy follows rule 6 ("flags potential", never "prevents"). Detailed
data contract is a **follow-on ADR**.

## Options Considered

1. **Naive optimizer loop** (propose → backtest → keep top Sharpe). Rejected: a
   multiple-testing false-positive generator; contradicts ADR-008 validation-first.
2. **LLM-as-judge** (agent reads metrics and decides "good"). Rejected: non-deterministic,
   non-reproducible, and precisely the failure mode of existing "AI trading" products. The
   agent's judgment is confined to *proposing* and *explaining*.
3. **MCP tools only, no persistent pool.** Rejected: without the immutable trial log we
   can't count trials for the Deflated Sharpe penalty and every agent re-searches blind.
4. **RAG-first / embed everything now.** Rejected as premature; structured storage answers
   the actual near-term queries. RAG is added when the pool needs semantic recall.
5. **This decision**: MCP (act) + trial-counted pool (remember) + deterministic gate &
   locked holdout (judge), LLM restricted to propose/explain.

## Consequences

Easier:
- "An AI that hunts strategies **and tells you honestly when it failed**" — a stronger,
  defensible story than "the AI found a winner", and it reuses the entire existing stack.
- Any agent (interactive, fork, cron) drives the same tools; findings compound.
- Reproducibility is intrinsic: a graduated strategy = a manifest hash you can replay.

Harder / new obligations:
- New surfaces to build & test: MCP server, experiment store, holdout splitter, search
  orchestrator, fundamentals source. Each lands ADR-first / TDD (this ADR is the umbrella;
  the experiment-store schema and the fundamentals data contract get their own ADRs).
- The holdout discipline is load-bearing and easy to violate — leaking it into a search
  tool silently invalidates every result. It must be enforced in code (search tools take a
  data handle that structurally cannot reach the holdout), not by convention.
- Paper/live trading (still out per ADR-001 until a superseding ADR) becomes the eventual
  proof stage; this ADR deliberately stops at "discovers holdout-validated strategies."

## Implementation sequence (each its own commit(s), ADR-first where non-trivial)
0. **Monte Carlo** wiring (risk tool: P(loss > X% in K bars)). Small, unblocks a risk gate.
1. **Experiment store + holdout splitter** (the pool substrate; own ADR for the schema).
2. **StrategyLab search orchestrator** — propose (grid + agent) → backtest → gate →
   leaderboard, trial-counted against the pool.
3. **MCP harness** exposing the tools so an agent drives the loop.
4. **Fundamentals/sentiment source** (own ADR for the data contract).
5. **Catalog expansion** — add advanced strategies as the search demands them.
6. **Forward/paper trading** — deferred; substrate decided once winners exist.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
