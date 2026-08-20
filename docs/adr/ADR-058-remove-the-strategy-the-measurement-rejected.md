# ADR-058: Remove `two_timescale_reversion` — and record what its rejection measured

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-056 §Consequences (the pre-stated removal criterion), ADR-057 (finalist attribution)
- **Relates to**: ADR-046 (candidate accounting), ADR-045 (capture efficiency), ADR-044 (search fingerprint)

## Context

ADR-056 added `two_timescale_reversion` to answer one question — does the band-reversion capture gap
come from the catalog having no strategy that separates a slow level from a fast deviation? — and
committed in advance to reporting the negative answer and considering removal. ADR-057 then made the
answer attributable. Both measurements are now in, at `n_bars=5400` on the 35-strategy catalog
(`search_config_version 2eede83f…`, Type-I error 0/200 on both nulls).

**Capture did not move.** Net capture at band half-lives 1/2/3/5/10/20 went
31.6 → 31.6, 29.5 → 30.0, 31.1 → 31.1, 44.6 → 45.3, 56.1 → 56.1, 58.4 → 58.4 percent. Detection
stayed 0/50 in every cell. The largest delta is +0.7pp.

**The attribution says why, and it is not the reason ADR-056 assumed.** Grouping each cell's 50
finalists by catalog category:

| band half-life | 1 | 2 | 3 | 5 | 10 | 20 |
|---|---|---|---|---|---|---|
| finalists from **Mean Reversion** | 18% | 44% | 64% | 94% | 94% | 82% |
| finalists from Trend | 68% | 44% | 24% | 2% | 4% | 14% |
| net capture | 31.6% | 30.0% | 31.1% | 45.3% | 56.1% | 58.4% |
| `two_timescale_reversion` wins | 1/50 | 2/50 | 4/50 | 5/50 | 1/50 | 2/50 |

On a process that is *by construction* fast reversion to a random-walk level, the max-DSR search
selects a **Trend** strategy 68% of the time at half-life 1. Capture tracks the recognition share
almost exactly: where the search identifies the process as reverting (half-life ≥ 5, 82–94% Mean
Reversion), capture is 45–58%; where it does not (half-life 1–3), capture is 30–31%. The control is
the AR(1) sweep from the same dispatch, where recognition is total and unambiguous: 100% Mean
Reversion finalists at φ = −0.2/−0.3, 66–74% Trend at φ = +0.2/+0.3, and a scattered mix only in the
|φ| = 0.1 cells where ADR-055 showed there is no achievable edge to recognize.

**So the fast-half-life gap is a RECOGNITION failure, not an expression failure.** Adding a 35th
reverting strategy could not have moved it, because at those half-lives no reverting strategy wins
the in-sample comparison at all — the selection step never gets far enough to ask which reverting
strategy is best. That is a sharper statement of the standing finding than ADR-056 was able to make,
and it is only available because the finalists' identities were recorded.

## Decision

**1. Remove `two_timescale_reversion` from the catalog** — all six touch points, exactly the
reversal ADR-056 wrote for itself.

It failed its own pre-stated criterion. It wins 1–5 of 50 searches per cell, adds at most +0.7pp of
capture in one cell, and under ADR-046 it taxes *every real symbol's* DSR/MinTRL denominator for as
long as it stays. The measured direction of that tax is visible in the same dispatch: all four
non-zero AR(1) detection cells moved down 2–4pp against the 34-strategy sweep (32/20/12/60% against
34/22/14/64%). Each delta is inside binomial noise at n=50 (SE ≈ 6.6pp), so this is not a claim of
significant power loss — it is a claim that the cost is real, the direction is what the accounting
predicts, and there is no measured benefit on the other side of it.

**Now is the cheapest possible moment.** No discovery run has executed since the strategy landed, so
no stored experiment references it and no pool row's trial count includes it. Removing after
tomorrow's 08:00 UTC run would leave the catalog and the pool permanently inconsistent about which
families were searched.

**2. Do not re-dispatch the calibration workflows for this removal.** Removing restores the exact
34-name list the previous artifacts were measured on, so `calibration_search_version` returns to
`3f36fda2…` — the fingerprint the committed Type-I and power records already carry. This is the
first use of ADR-044's fingerprint as an *identity* rather than a warning: the calibration matching
the restored catalog already exists. The restored fingerprint is asserted by a test, so a silent
drift in the hash function cannot let a stale artifact be reused.

**3. The next unit is the selection step, not another strategy.** ADR-056 §Consequences guessed the
estimator; the attribution says recognition. Whatever is tried next must be judged the same way:
against the finalist *category mix* at half-lives 1–3, not against capture alone.

## Alternatives considered

- **Keep it and judge it on real symbols after tomorrow's discovery run.** Rejected, though it was
  close. It is the reversible-looking option but it is the more expensive one: the trial-count tax
  starts applying to every real symbol immediately, the pool becomes inconsistent with any later
  removal, and the hypothesis it would test ("real markets differ from the planted process") is
  unfalsifiable in the direction that matters — a strategy that never wins would read as "not yet".
- **Keep it because the test could not have rewarded it.** The strongest counter-argument: at
  half-lives 1–3 no reverting strategy wins, so expression was never really tested. Rejected because
  at half-lives 5–20, where recognition *does* work, the strategy competes and loses to plain
  `mean_reversion` (5/50 against 18/50 at half-life 5) for +0.7pp of capture. It got a fair test
  where a fair test was possible.
- **Keep it and widen its grid.** Rejected: a strategy that must be re-tuned to earn its place is
  being fitted to the calibration harness, which ADR-056 already rejected as the one thing that
  would destroy the instrument.
- **Remove it and also re-dispatch all three workflows.** Rejected as unnecessary given decision 2,
  and mildly harmful: three fresh runs would produce numerically different artifacts (different RNG
  draws are not involved, but re-writing them invites the reader to treat them as new evidence)
  for a catalog that is bit-for-bit the one already measured.

## Consequences

- The catalog returns to 34 single-name strategies and to `search_config_version 3f36fda2…`; the
  committed Type-I and power records apply again without a re-run.
- ADR-056 keeps Accepted status. It was a correct decision that produced a real result — the
  experiment answered its question in the negative and produced a sharper finding than the one it
  set out to test. This ADR is its conclusion, not its retraction.
- The project now has a worked example of adding a strategy, measuring it against a pre-stated
  criterion, and removing it. That loop is worth more than the strategy would have been.

## Reversal

Restore the file, config, builder branch, catalog entry and tests from commit `c005334` and bump the
two documented counts back to 35. Then re-dispatch all three calibration workflows together at the
same `n_bars` (`validation-methodology.md` §7.2) — the restored 35-name fingerprint has committed
artifacts too (`2eede83f…`), so strictly the re-dispatch is only needed if the catalog is restored
in a *different* form than ADR-056 shipped.
