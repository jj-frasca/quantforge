# ADR-109: Report a confidence interval on a single backtest's Sharpe estimate

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)

## Context

`BacktestMetrics.sharpe` is a bare point estimate. Every existing statistic that puts a number
next to it — PBO, DSR, walk-forward, purged CV — answers a **selection-bias** question ("is this
Sharpe distinguishable from the best of a search that tried many configurations?"). None of them
answer a much more basic question about the same number: **how much sampling noise is in this one
estimate, given only `T` years of return history?** A Sharpe of 1.2 estimated over 15 years of
daily data and a Sharpe of 1.2 estimated over 6 months carry very different amounts of information,
and `BacktestMetricsView` currently reports them identically.

This project already has the answer implemented and load-bearing elsewhere: ADR-043's
`app/research/lab/frontier.py` computes `sharpe_standard_error` from Lo (2002) — the
asymptotic standard error of an annualized Sharpe estimated over `T` years,
`sqrt((1 + SR^2/504) / T)` — to size the detectable-edge frontier. That is a **population-level**
calculation (given a hypothetical true Sharpe and a fixed holdout design, what's detectable) built
on `app/research/lab/universe.py`'s null machinery. What's missing is the much simpler, per-result
use of the same formula: given an **already-observed** Sharpe and the **actual** sample size,
what's the interval around it?

`app/research/backtesting/` sits below `app/research/lab/` in this codebase's layering (`lab/`
imports from `backtesting/`; nothing in `backtesting/` imports from `lab/`, confirmed by grep
before writing this ADR) — a `metrics.py` function cannot import `frontier.py`'s implementation
without inverting that direction. This ADR re-derives the same well-established asymptotic
formula at the lower layer rather than either restructuring `frontier.py`'s dependency shape
(out of scope, touches ADR-043's identity) or skipping the feature.

## Options Considered

1. **Add `sharpe_confidence_interval` to `app/research/backtesting/metrics.py`, re-deriving Lo
   (2002)'s formula locally (same math as `frontier.py`, independent implementation, both cite the
   same paper), `None` when there's under a year of data (the asymptotic approximation is
   unreliable below that, same reasoning `frontier.py`'s power calibration already respects via
   its own `holdout_years` design constraint).**
   - Pro: no layering violation; a genuinely new descriptive answer (sampling uncertainty), not a
     restatement of Sortino/Calmar's risk-shape question or DSR/PBO's selection-bias question.
   - Con: the SE formula now has two independent call sites (`frontier.py`, `metrics.py`) that
     must be changed together if either the formula or its annualization convention ever changes.
2. **Move `sharpe_standard_error` down into `backtesting/metrics.py` and have `frontier.py` import
   it from there instead of defining its own.**
   - Pro: single implementation, zero duplication.
   - Con: changes ADR-043's module and its fingerprint/identity for a benefit (avoiding one
     ~10-line duplicated function) that doesn't justify touching validated, peer-adjacent
     calibration code for an unrelated feature. Rejected as disproportionate blast radius.
3. **Do nothing; a reader can eyeball `n_trades`/the equity curve length and guess at reliability.**
   - Pro: zero cost.
   - Con: leaves exactly the kind of unstated uncertainty CLAUDE.md rule 6 (data-quality honesty)
     and this project's whole validation-layer ethos argues against — a number presented without
     its own noise band understates how little a short backtest actually says.

## Decision

Add `sharpe_confidence_interval(returns: pd.Series, *, confidence: float = 0.95) ->
SharpeConfidenceInterval | None` to `app/research/backtesting/metrics.py`. Computes the annualized
Sharpe's standard error via Lo (2002), `sqrt((1 + SR^2 / (2*252)) / years)` with
`years = len(returns) / TRADING_DAYS`, and returns `(lower, upper)` using `scipy.stats.norm.ppf`
(already a project dependency, used identically in `app/validation/deflated_sharpe.py`). Returns
`None` when there are fewer than 2 returns (Sharpe itself is undefined) or fewer than 1 year of
data (below which the asymptotic normal approximation is unreliable). Wired as
`BacktestMetrics.sharpe_ci` (nullable) and the matching nullable field on `BacktestMetricsView`.
Descriptive only, like Sortino/Calmar: no gate, PBO, or DSR calculation reads it, and it makes no
argument about any threshold (charter §4 unaffected).

**Scope of this ADR is backend + API only.** Frontend display is deliberately deferred: `zod`'s
default `z.object()` strips unknown response keys rather than rejecting them (confirmed in
`src/types/backtest.ts`'s existing schema — no `.passthrough()`/`.strict()`), so an additional
backend field the frontend schema doesn't yet know about is silently ignored, not a breaking
change. This keeps the backend slice complete and independently valuable (the API contract is
correct and tested on its own) without forcing a same-commit frontend diff for a field whose UI
treatment (a range on a chart tooltip? inline text next to the point estimate?) deserves its own
consideration rather than reusing the Sortino/Calmar `<dt>/<dd>` pattern verbatim for a
fundamentally different, nullable, two-number shape.

## Consequences

- `/backtest` responses gain a `metrics.sharpe_ci` field that is `null` for short backtests (under
  a year of data) and a `{confidence, lower, upper}` object otherwise — callers must handle null.
- A new Hypothesis property test asserts `lower <= sharpe <= upper` whenever the interval exists
  (true by construction from a symmetric z-interval, but worth locking down as a regression guard)
  and that the interval is `None` below one year of data. This is descriptive infrastructure, not
  one of the §8 "ALL required" financial-math invariants (it doesn't constrain a value's valid
  range the way PBO ∈ [0,1] does) — no new §8 entry.
- `.claude/context/backtesting-spec.md` and `api-contracts.md` document the new field and its
  nullability explicitly, so a future session doesn't assume it's always present.
- Nothing in the gate, calibration, or pool-report layer reads this field.
- Frontend display is untracked future work — noted in `.claude/RUNNING_STATE.md`, not silently
  dropped.

## Reversal
Delete `sharpe_confidence_interval`, `SharpeConfidenceInterval`, the `sharpe_ci` field, and its API
plumbing. Nothing else depends on it.
