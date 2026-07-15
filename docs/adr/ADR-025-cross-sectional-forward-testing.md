# ADR-025: Cross-sectional forward-testing

- **Status**: Accepted
- **Date**: 2026-07-15
- **Deciders**: Joe Frasca
- **Extends**: ADR-024 (cross-sectional strategy dimension), ADR-019 (forward-testing / paper
  trading), ADR-020 (managed lifecycle exits)

## Context
ADR-024 landed the cross-sectional engine: a factor is ranked across the whole universe each period,
realized as **one dollar-neutral long/short portfolio return series**, and put through the same
graduation gate a single-name strategy must clear (DSR / PBO / stability / MinTRL / locked-holdout
Sharpe / beat-benchmark). Its Consequences named the next obligation explicitly: *forward-test
survivors like single-name graduates*.

Single-name graduates already have that machinery (ADR-019/020): `paper.evaluate_forward` scores a
frozen graduate ONLY on bars after its freeze date, `ExitPolicy` + `lifecycle_from_returns` cut a
position whose rolling forward Sharpe decays or stops beating buy-and-hold, and
`portfolio_manager.manage_portfolio` promotes new graduates + monitors/exits open ones across a hunt.
That machinery is **single-series by contract**: a `PaperPosition` is one `symbol`, and
`evaluate_forward` runs `BacktestEngine` over one close series and benchmarks against holding that
one name.

A cross-sectional graduate is not one symbol — it is a whole portfolio over a universe. Its honest
out-of-sample question is not "did strategy X beat holding AAPL?" but "did this long/short factor
keep earning, out of sample, versus simply holding the equal-weight universe long-only?" — the exact
benchmark ADR-024 used at the holdout boundary. It therefore needs its own forward-testing design
that mirrors the *shape* of ADR-019/020 while operating on panels and portfolio returns.

## Decision
Add a new, self-contained module `backend/app/research/cross_sectional/forward.py` that forward-tests
cross-sectional graduates. It reuses the ADR-024 engine (`portfolio_returns`, `asset_returns`) and the
registry (`default_strategies`) unchanged, and mirrors `paper.py` / `portfolio_manager.py` at the
**portfolio** level. It does **not** modify the cross-sectional engine files, the single-name catalog,
or `universe.py`.

### (a) How a cross-sectional graduate is forward-tested
A graduate is frozen as a `CrossSectionalPosition` (strategy name, searched parameters *including the
quantile*, the universe symbols, the cost rate, an optional value-score map for `xs_value`, and a
`frozen_at` boundary). To score it, rebuild the factor's signal function from the **unmodified**
registry, recompute the engine's `portfolio_returns` over the **full** panel (so momentum lookbacks
are warmed up by the freeze boundary), and score **only the post-`frozen_at` slice** — genuinely
unseen bars. This is the panel analog of `evaluate_forward`'s "run the engine over the full frame,
score the post-freeze slice". Because every engine step is causal (`weights.shift(1)`), the forward
slice depends only on prices ≤ its own dates: **no look-ahead** — forward returns use only
post-holdout bars, weights at `t` use prices ≤ `t`.

### (b) The benchmark
The equal-weight **long-only** universe return — `asset_returns(panel).mean(axis=1)` on the same
forward slice. This is exactly ADR-024's holdout benchmark (the cross-sectional analog of "why not
just hold it?"). The honest forward bar is: did the dollar-neutral factor out-earn holding the whole
universe equal-weighted, risk-adjusted, on data it never saw?

### (c) The lifecycle exit (analogous to ADR-020)
A `CrossSectionalExitPolicy` (tunable + versioned, same philosophy as `ExitPolicy` / `GateConfig`)
retires a factor when, on its forward returns: (1) the rolling out-of-sample Sharpe falls at or below
a floor (`min_rolling_sharpe`), or (2) the forward drawdown breaches a limit, or (3) it stops beating
the equal-weight benchmark on the rolling window. A grace period (`min_forward_bars_before_exit`)
avoids cutting on entry noise, and a trailing `rolling_window_bars` window means recent decay is not
masked by early gains — identical structure to `lifecycle_from_returns`, only the benchmark is the
equal-weight universe rather than a single name's buy-and-hold. Retirement is a one-way transition:
a retired factor is kept as an honest record and never re-promoted.

### (d) What state persists
A per-factor **forward record** (`CrossSectionalPosition`), persisted as a JSON-file book
(`JsonFileCrossSectionalForwardBook`, mirroring `JsonFilePaperPortfolio` / the ADR-024 store's
JsonFile pattern with a trailing newline so the end-of-file-fixer hook stays green). Each record
carries: the frozen factor spec, its latest `CrossSectionalForwardScore` (cumulative out-of-sample
return + bars + Sharpe, the benchmark return/Sharpe, `beats_benchmark`, `as_of`, and a per-bar
normalized forward equity curve à la ADR-023), the current `status` (`open` | `retired`),
`retired_at`, and the `exit_reasons`.

### In scope
- Frozen models: `CrossSectionalForwardScore`, `CrossSectionalForwardEquityPoint`,
  `CrossSectionalPosition` (with `status` / `exit_reasons`), `CrossSectionalExitPolicy`,
  `CrossSectionalLifecycleDecision`.
- Pure functions: `score_forward` (factor forward returns vs equal-weight benchmark),
  `lifecycle_from_returns` + `evaluate_lifecycle` (apply the exit), `promote_graduate` (freeze a
  graduated `CrossSectionalExperiment`), and `manage_book` (promote new graduates + monitor/retire
  open ones across a new hunt, injectable over a panel provider).
- A `JsonFileCrossSectionalForwardBook` JSON store, and optionally a thin driver script.

### Out of scope (deferred)
- Real-broker execution of a dollar-neutral cross-sectional book (ADR-021 is single-name equity
  sizing). A live long/short book needs shorting/borrow modeling — a later ADR.
- A scheduled cloud cron and frontend surface for the cross-sectional forward book (the single-name
  paper loop has both; this ADR lands the engine + store only).
- Time-varying value re-ranking of `xs_value` forward (ADR-024 already freezes value on a static
  as-of snapshot; point-in-time value history is its own later ADR).
- Cross-strategy / universe-level deflation of the forward track record.

## Options Considered
- **Reuse `paper.PaperPosition` / `evaluate_forward` directly.** Rejected: those are single-symbol by
  contract (`PaperPosition.symbol`, `BacktestEngine.run_strategy` over one close series, benchmark =
  that one name's buy-and-hold). A cross-sectional factor is a panel + a portfolio; forcing it through
  the single-name path would distort both the signal reconstruction and the benchmark.
- **Benchmark the forward factor against a zero return (absolute Sharpe only).** Rejected: a
  dollar-neutral factor can post a positive Sharpe purely from a market drift leaking through
  imperfect neutrality. ADR-024 already settled the honest bar at the equal-weight long-only universe;
  the forward test must use the identical benchmark for continuity.
- **Invent a parallel lifecycle for portfolios.** Rejected on the same grounds as ADR-024's gate
  reuse: the risk discipline should be the *same shape* a single-name position clears. We mirror
  `ExitPolicy` / `lifecycle_from_returns` exactly; only the benchmark input differs.
- **Re-run the whole search each forward step instead of freezing the finalist.** Rejected: that is
  re-fitting on the forward data — the precise look-ahead the freeze boundary exists to prevent. The
  factor's config is locked at graduation; forward bars only score it.

## Consequences
- Cross-sectional graduates accrue a genuine out-of-sample track record over real time, exactly as
  single-name graduates do — closing ADR-024's stated next obligation without weakening any rigor
  (the freeze boundary, the equal-weight benchmark, and the lifecycle exit all carry over).
- New obligation for whoever integrates further: wire `manage_book` into a scheduled cross-sectional
  hunt driver + cloud cron (token-free, like the single-name paper loop), and surface the forward book
  on the dashboard. A real-broker long/short execution path remains a separate, larger build.

---
*ADRs are immutable (CLAUDE.md rule, ARCHITECTURE.md §2.3). To change a decision, write a
new ADR that supersedes this one; never edit an accepted ADR.*
