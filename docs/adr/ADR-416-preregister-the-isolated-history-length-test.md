# ADR-416: Pre-register the isolated history-length test for `xs_quality`

- **Status**: Accepted — design only. **Not yet dispatched.**
- **Date:** 2026-11-06
- **Deciders:** Interactive session (Joe present), same session as ADR-414/415/FINDING-350
- **Acts on:** FINDING-350's addendum, which found the first `history_start=1990-01-01` dispatch
  confounded on three variables at once (universe breadth, history length, and `lifetime_trials`)
  and explicitly deferred a clean test to its own pre-registered ADR.
- **Relates to:** ADR-063/070/094/161 — this project's repeated, consistent lesson: state the
  comparison before you can see its answer.

## Context

FINDING-350's addendum measured `xs_quality` at Sharpe 0.682 with a 1990-start, 235-symbol panel,
still short of MinTRL by ~5.8 years despite available history nearly doubling (17.4y → 29.5y). That
result cannot be attributed to history length alone: the universe also broadened from 51 to 235
symbols, and `lifetime_trials` grew from the low-3,000s to 3,672 across the comparison, each of
which independently moves the result in an unknown direction and magnitude.

**The isolated test holds everything constant except the one variable in question.**

## Decision

**Pre-register, run once, read as specified — no post-hoc adjustment of any field below.**

1. **Universe (fixed, both arms).** `data/universes/large_cap_fixed36.txt` — the 36 symbols from
   the original `large_cap.txt` (51 symbols) independently verified this session to have real Q1
   1990 price data (`>= 55` trading bars in a Jan–Mar 1990 window; same verification method ADR-414
   used). This is a SUBSET of `large_cap.txt`, not the 235-symbol `large_cap_longhistory.txt` — the
   point of this design is to hold breadth fixed, not to maximize it.
2. **Arm A (baseline).** Dispatch with `universe=data/universes/large_cap_fixed36.txt`,
   `history_start` unset (default `RECENT_HISTORY_START`, 2005-01-01).
3. **Arm B (treatment).** Dispatch with the SAME universe file, `history_start=1990-01-01`.
4. **Run order.** Arm A first, then Arm B, back to back, minimizing the `lifetime_trials` drift
   between them from unrelated background search activity (Codex, scheduled single-name hunts).
   The drift cannot be eliminated — the denominator is global and shared — so record each arm's
   own `lifetime_trials` at read time and report the delta explicitly; do not assume it is zero.
5. **Comparison.** For `xs_quality` specifically (not best-of-family — the question is about this
   one strategy's own MinTRL margin, not which family wins selection, which ADR-060 already
   established is a separate, noisier question):
   - `observed_sharpe` in each arm.
   - `minbtl_years(lifetime_trials, observed_sharpe)` in each arm — the required MinTRL.
   - Available in-sample years in each arm (`0.8 ×` the panel's actual calendar span — read from
     `panel_manifest`, never assumed from the nominal `history_start`).
   - **The margin**: available − required, in each arm. This is the single number this test
     exists to compare.
6. **Pre-stated reading** (first match wins):
   - **History length helps**: Arm B's margin is less negative (or positive) than Arm A's, by more
     than the margin's own sensitivity to a `lifetime_trials` change of the size actually observed
     between the two arms (i.e., the improvement survives recomputing Arm A's required-years at
     Arm B's own N).
   - **History length does not help**: Arm B's margin is equal to or more negative than Arm A's,
     after the same N-adjustment.
   - **Confounded / no clean reading**: the two arms' `lifetime_trials` differ by enough that the
     N-adjustment itself dominates the comparison (state the threshold as a >10% relative change in
     required years from N alone, computed before looking at either arm's margin).
7. **Single look.** No sequential design, no re-run on an unfavorable result, no retry with a
   different universe or holdout fraction. A different design needs its own ADR.
8. **Cost, stated up front.** Both arms add `xs_quality`'s own trial plus every other registered
   family's trial (15 price-only factors, per the full breakdown in FINDING-350's addendum) to the
   SAME global `lifetime_trials` denominator every other search — single-name and cross-sectional
   alike — now has to clear. At the time of writing, `lifetime_trials = 3,672`. Running both arms
   adds roughly 32 more trials (16 strategies × 2 arms), pushing the next unrelated search's own
   MinTRL bar up by `ln(3704/3672) ≈ 0.9%` — small per this pair, but this project has now run two
   cross-sectional dispatches in one session partly to test a single hypothesis, and that pattern
   does not scale to repeated casual re-tests.

## What this is NOT

- Not a weakening of any gate, threshold, or the MinTRL formula itself.
- Not a claim about which family wins selection — ADR-060 already settled that single-name
  selection is noisy; this test is scoped to `xs_quality`'s own margin only.
- Not a license for a future session to "try again with a bigger universe" if this comes back
  unfavorable. A different design is a different ADR, not a retry of this one.

## How to reverse

Delete `data/universes/large_cap_fixed36.txt`. Nothing depends on its existence until Arm A is
actually dispatched.

## Measured (2026-11-06, single look, read as pre-registered)

Universe `large_cap_fixed36.txt` (36 symbols) in both arms; `xs_quality` only; available years = 0.8 x panel span from `panel_manifest`; required = `minbtl_years` (2 ln N / SR^2) at each arm's own `lifetime_trials`.

| Arm | Run / commit | Panel start | N | xs_quality Sharpe | Required (y) | Available (y) | Margin (y) |
|---|---|---|---|---|---|---|---|
| A (2005) | 42174863467 / 0c8deaf9 | 2005-01-01 | 3,807 | 0.438 | 85.8 | 17.5 | -68.3 |
| B (1990) | 42175645397 / 5c255140 | 1990-01-01 | 4,077 | 0.521 | 61.2 | 29.5 | -31.7 |

- **N-adjustment (§6):** recomputing Arm A at Arm B's N gives required 86.7y, margin -69.2y. The N effect on required years is ~1% (ln 4077 / ln 3807), far under the 10% confounding threshold, fixed before reading margins.
- **Pre-stated reading: history length helps** -- Arm B's margin is ~37 years less negative than Arm A's after N-adjustment. **But the margin is still deeply negative (-31.7y); `xs_quality` does not clear MinTRL in either arm.** Part of the gain is a higher Sharpe in Arm B (0.438 -> 0.521), which is itself a history-window effect; the test does not separate "more years" from "different years' Sharpe".
- **Deviations, disclosed:** (1) Arm B's first dispatch (42174912568) computed but failed to push (pool-JSON rebase conflict with Arm A's commit), so nothing landed; it was re-dispatched once (42175645397) as a mechanical retry, and the landed result is the one reported. (2) An extra, unplanned default-start run on the same universe landed in between (42175215554 / 68484cf1, N=3,942, Sharpe 0.438, required 86.2y) -- it reproduces Arm A (same Sharpe) and does not change the reading. Total added trials were therefore higher than the ~32 estimated in §8.
- **Context:** the 36-symbol subset Sharpe (0.44-0.52) is well below the 51-symbol 2005 best (0.96) and the 235-symbol 1990 run (0.68): `xs_quality`'s Sharpe is sensitive to universe composition, which this test held fixed but did not explain. No gate was changed. SINGLE LOOK IS USED; no re-dispatch.
- **Deviation (3), disclosed (added by a second, uncoordinated interactive session executing this
  same pre-registered design in parallel):** a third dispatch (`42175825153`, `history_start=
  1990-01-01`, the same universe) computed a result but failed to push — a JSON merge conflict
  against this ADR's own Arm B commit (`5c255140`), which the workflow's retry logic cannot
  auto-resolve for two concurrent appends to the same array. That result never landed in
  `data/cross_sectional_pool.json` (confirmed: no experiment created after 06:40 UTC exists in the
  pool) and no number from it is reported anywhere. It is not treated as a third measurement and
  does not reopen this single look — the reading above, from the two arms that did land, stands as
  written. Recorded here only so the operational collision (two sessions independently dispatching
  the same freshly-committed ADR within minutes of each other) is part of the honest record, the
  same disclosure standard this ADR already applies to deviations (1) and (2).
