# ADR-094: Pre-register a within-symbol truncation test for the cohort-magnitude question

- **Status**: Accepted
- **Date**: 2026-09-22
- **Deciders**: Autonomous session #95 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-093 (history coverage), the three calibration cohorts it triggered
  (`bootstrap_spy`/`iid_normal` at 6,075 / 7,400 / 9,247 bars)
- **Relates to**: ADR-063 (`SEARCH_HISTORY_START=1990-01-01`, the reason the pool is bimodal by
  listing age), ADR-068 (the drift-controlled walk-forward excess statistic), ADR-074/075/076 (the
  established pattern this ADR reuses: pre-register a frozen sample, pair within symbol, read a
  drift-controlled delta with a bootstrap interval)

## Context

Three same-day calibration dispatches (`ebbb6b0f`, `83e6f86e`, docs `15c6860e`/`d3d828c4`) gave the
pool's walk-forward excess a reading at three history lengths. It is **not monotonic**: 6,075 bars
spans zero (**−0.018 [−0.067, +0.008]**), 7,400 bars is the largest and excludes zero (**−0.122**),
9,247 bars excludes zero but is smaller (**−0.047**). The session that measured this explicitly
ruled out "more history → smaller apparent edge" as too simple and named the open question: is the
7,400-vs-9,247 gap a **history-length effect** (a longer holdout genuinely changes what the
walk-forward split measures), or a **cohort-composition effect** (the 9,247-bar cohort is, by
`SEARCH_HISTORY_START`'s construction, exactly "every symbol listed before 1990" — a population that
may differ from the 7,400-bar cohort in ways the search never sees: sector mix, size, survivorship)?

These two hypotheses make different predictions under one operation the pool cannot currently
answer either way: **take a symbol that naturally lands in the 9,247-bar cohort and re-search it
using only its own most recent 7,400 bars.** If the excess is a history-length effect, the truncated
re-search should move toward the 7,400 cohort's larger-magnitude excess. If it is a
cohort-composition effect, the truncated re-search — same symbol, same drift, same everything except
how much of it the search sees — should stay near the symbol's own natural (9,247-bar) reading. This
is exactly the logic ADR-074/076 already used to test whether extending `SEARCH_HISTORY_START` from
2005 to 1990 changed the drift-controlled excess (it measured no significant change,
**−0.008 [−0.055, +0.022]** at the Pocock boundary) — but that experiment's "long" side was the
symbol's *natural* full-1990-window length (median 9,232 bars in the frozen sample), so it never
isolated a length effect *within* the saturated cohort the way this one does. It answers a related
but distinct question and does not substitute for this one.

`compare_search_windows` already implements exactly the paired, drift-controlled comparison this
needs, but its `WINDOW_SPLIT_BARS = 6000` threshold cannot separate this experiment's two sides —
both a truncated-to-7,400 search and a natural ~9,247-bar search land on the same ("long") side of
6,000, so the existing pairing would never form. This ADR's implementation slice
(`fe1e2c3d`-equivalent commit) generalized `compare_search_windows` to take a `split_bars` override
and added `history_length_experiment_symbols` for candidate selection — both tested, no behavior
change to any existing caller (default `split_bars=WINDOW_SPLIT_BARS`).

## Decision

**Run a within-symbol truncation experiment, following the ADR-074/076 pattern exactly:**

1. **Candidates**: symbols whose longest recorded search already reaches `min_n_bars=8500` (clear
   headroom above the truncation target, so the pairing split at `split_bars=8000` never straddles
   an ambiguous case) and which already carry ADR-068's `walk_forward_hold_sharpe` benchmark. Locally
   measured: 266 such symbols exist in the pool today.
2. **Truncation target**: `CALIBRATION_N_BARS = 7,400` (the existing named constant, already the
   length of the largest-magnitude cohort) — each candidate's already-fetched frame, from
   `SEARCH_HISTORY_START`, is truncated to its most recent 7,400 rows (`frame.tail(7400)`) rather
   than re-fetched from a computed start date. This sidesteps calendar-vs-trading-day ambiguity
   entirely: the truncated frame is an exact suffix of the same series the natural search used.
3. **Sample size n = 100**, frozen to `data/history_length_experiment/adr094_sample.json` and
   committed **before** any of it is searched (ADR-076 decision 1's rule, for the same reason: the
   candidate list is a property of today's pool and would silently re-roll if re-derived later).
   Locally timed at ~8s/symbol (fetch + 35-strategy search with refine) — n=100 is a foreground-run
   budget of roughly 15 minutes, not a multi-session dispatch like ADR-076's 200.
4. **This is a first look, not a sized-to-detect-the-effect look**, unlike ADR-076 (which derived
   n=200 from look 1's measured dispersion). There is no prior dispersion estimate for *this*
   statistic to size against — ADR-074's original n=45 mistake was treating an arbitrary n as if it
   were principled; this ADR is explicit that n=100 is a local-compute-budget choice, and a null
   result (CI spans zero) is **underpowered, not negative** unless the interval is tight enough to
   rule out effects of the magnitude in question (~0.07, the 7,400-vs-9,247 raw gap). A clear
   directional signal is still informative regardless of power; scaling to a sized second look
   (mirroring ADR-074→076) is the natural next step if this first look is ambiguous and the question
   is judged worth spending a second look's Type-I budget on.
5. **Single look, read at 95%.** No sequential design is pre-committed — if this first look is
   ambiguous, a follow-up ADR must size and pre-register its own sample (a fresh look, or an
   explicit two-look design against this one), exactly as ADR-076 did for ADR-074.
6. **Written to `data/history_length_experiment/`, never to `data/research_pool/`** (ADR-030: one
   writer per generated file; this experiment's rows are not production search output and must never
   be read as part of the discovery pool's trial prior in a way that double-counts them).
7. **The comparison itself**: `compare_search_windows(natural_pool_experiments + truncated_results,
   split_bars=8000)`, reading `excess_delta_median` — `(natural_excess) − (truncated_excess)`. A
   delta near zero with a tight CI says truncation does not move the excess (cohort composition, not
   length); a delta whose CI excludes zero in the direction that shrinks the truncated side's excess
   magnitude says length itself matters.

## Alternatives considered

- **Re-fetch from a computed calendar start date** (mirroring `PRE_ADR063_SEARCH_START`'s fixed
  literal). Rejected: bars-per-calendar-day varies by symbol (holidays, historical trading-halt
  gaps), so a fixed date would not reliably yield exactly 7,400 bars per symbol, reintroducing
  exactly the kind of `n_bars` fuzziness `HISTORY_TOLERANCE` exists to paper over. Truncating the
  already-fetched frame to its most recent 7,400 rows is exact by construction and needs no
  tolerance.
- **Compare against the null artifacts directly instead of pairing within symbol.** Rejected: that
  is what the three calibration dispatches already did, and it is exactly the comparison that
  produced the open, confounded question this ADR exists to resolve. Pairing within symbol is the
  only design that holds sector/size/survivorship/drift fixed and isolates history length.
- **Truncate to 6,075 bars instead of 7,400.** Rejected: 7,400 is the cohort with the *larger*
  excess magnitude, so it is the more informative target — if truncation reproduces a 7,400-like
  reading, that is the stronger and more surprising result. 6,075 is available as a second slice
  later if this one is ambiguous.
- **Size n from ADR-076's dispersion estimate (σ≈0.254 per-symbol delta).** Considered but rejected
  as unjustified transfer: that SD was measured for the 2005-vs-1990 window delta, a different pair
  of windows and possibly a different underlying dispersion. Borrowing it to size this experiment
  would repeat ADR-074's original error (an unstated assumption dressed as a calculation) in the
  other direction. n=100 is stated plainly as a compute-budget choice instead.

## Consequences

- Adds `history_length_experiment_symbols` and a `split_bars` parameter on `compare_search_windows`
  to `app/research/lab/pool_report.py` (tested; default behavior of every existing caller is
  unchanged).
- Adds `scripts/history_length_experiment.py` (local-only, live network, never in CI — same posture
  as `scripts/window_experiment.py`).
- `data/history_length_experiment/` is a new generated-state directory; this session is its sole
  writer for the shards it produces (ADR-030).
- Does not touch `data/research_pool/`, any null-calibration artifact, or any production gate
  threshold. Fully additive and reversible.

## How to reverse

Delete `scripts/history_length_experiment.py`, `data/history_length_experiment/`,
`history_length_experiment_symbols`, and the `split_bars` parameter (restoring
`compare_search_windows`'s old fixed-`WINDOW_SPLIT_BARS` behavior — no other caller passes the new
parameter, so removing it is a pure revert). No stored production artifact is affected in either
direction.

## Measured

Pending — see `RUNNING_STATE.md` for whether the frozen sample has been searched and reported in
this session or a later one.
