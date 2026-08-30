# ADR-070: The walk-forward selection rule failed its pre-stated criterion; the default stays

- **Status**: Accepted
- **Date**: 2026-08-30
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-069 (which stated this criterion before the run)
- **Relates to**: ADR-063 (whose criterion failed the same way), ADR-041/049 (power), ADR-055

## Context

ADR-069 made the finalist selection rule a parameter and stated, before running anything:

> Switch the default to `walk_forward` only if, at the same seeds and lengths, detection **rises in
> at least one** of φ = −0.3, −0.2, +0.2, +0.3 and **falls in none**, and the null's
> false-graduation rate stays at 0/200 on both nulls.

Both arms were then measured by the same code on the same planted symbols — `autocorrelated_edge`
is deterministic in its seed, so the two runs differ in the ranking key and in nothing else.

## Measured

**`observed` arm**: `data/power_calibration/ar1.json`, run 33272143102, fingerprint `3f36fda2…`.
**`walk_forward` arm**: run **33288580666**, fingerprint `9f7db739…`, 50 symbols per cell, seed 0,
7,400 bars — identical settings, not committed by design (ADR-069's amendment).

| φ | −0.30 | −0.20 | −0.10 | +0.10 | +0.20 | +0.30 |
|---|---|---|---|---|---|---|
| detection, `observed` | 40% | 36% | 0% | 0% | **24%** | 66% |
| detection, `walk_forward` | **44%** | 36% | 0% | 0% | **22%** | **74%** |
| clears the ADR-018 bar, `observed` | 20/50 | 10/50 | 0 | 0 | **11/50** | 33/50 |
| clears the bar, `walk_forward` | **22/50** | **11/50** | 0 | 0 | **9/50** | **37/50** |

**The criterion FAILED.** Detection rose at φ = −0.30 (+4pp) and +0.30 (+8pp), held at −0.20, and
**fell at φ = +0.20, from 24% to 22%** — one symbol of fifty. "Falls in none" is not satisfied, so
**the default stays `observed`.** Recorded as failed rather than reinterpreted, exactly as ADR-063's
was: the whole value of stating a criterion in advance is that it is allowed to say no.

The measurement is nonetheless informative, and both things are true at once:
- Aggregated over the four cells with an edge to find, detection went **63/200 → 66/200** and
  clearing the ADR-018 bar went **74/200 → 79/200**. Every movement is small.
- The single fall is **one symbol** (12 detections → 11). At p ≈ 0.24 and n = 50 the binomial
  standard error is ±6pp, so a 2pp move is far inside noise — and so, individually, are the +4pp and
  +8pp rises. The arms are not distinguishable at this sample size in either direction.
- ADR-060 already said the family the search picks leads the runner-up by a third of one standard
  error. **A ranking key applied to families that are not separable should not be expected to move
  detection much, and it did not.** That is a coherent result, not a null one.

### The meta-lesson, and it is the second time

ADR-063's criterion failed because it was phrased over cells with nothing to find. This one failed
because it was phrased over **per-cell raw rates whose standard error (±6-7pp) is three times the
movement any plausible improvement would produce**. Both are the same mistake in different clothing:
*a pre-stated criterion has to be phrased at a resolution the measurement can actually deliver.*

**Standing rule for the next criterion of this kind, and it is now cheap to follow: compute the
standard error of the statistic BEFORE stating the threshold, and state the criterion on an
aggregate whose SE is smaller than the effect you would act on.** Here that would have been "total
detections across the four cells (n=200, SE ±3pp) must rise by more than one standard error" — which
this run would ALSO have failed (63 → 66 is 1pp of 200, well inside ±3pp), reaching the same
decision by a route that could have distinguished a real improvement from noise.

## Decision

1. **The default selection rule stays `observed`.** No production workflow changes.
2. `select_by` stays in the code and in both drivers/workflows. It cost nothing, it is
   fingerprinted, and the next attempt at the selection step should not have to rebuild it.
3. **Do not re-run this comparison at n = 50.** A rematch needs n ≈ 400 per cell to resolve a 5pp
   difference, which is 8× the compute of tonight's run — cheap in wall-clock terms (this one took
   ~7 minutes) and worth doing only alongside a selection rule with a stronger prior than this one.
4. The second clause of ADR-069's criterion — Type-I error at 0/200 under the new rule — was
   dispatched as run **33288583470** and is recorded there. It cannot rescue a failed first clause,
   and no default moves on it either way.

## Alternatives considered

- **Call it a win on the aggregate.** Rejected: the criterion said "falls in none", and rewriting a
  criterion after seeing the numbers is the one thing this project's method forbids. The aggregate
  is reported *and* shown to fail an honest version of the same test.
- **Declare the arms equivalent and switch on principle** (a prequential key is better statistics
  than an in-sample argmax). Tempting and still plausibly true, but ADR-069 pre-committed against
  exactly this: "a selection rule that picks the category a human would have picked, without
  detecting more planted edge, has improved a narrative and nothing else."
- **Re-run at n = 400 tonight.** Rejected as the wrong next move rather than as expensive: the prior
  that a ranking key changes anything is weak (ADR-060), so the compute belongs on a rule with a
  better one — for instance ADR-068's excess-over-hold key, once the pool carries the benchmark.

## Consequences

- The selection step remains the open target, and is now the open target with one measured
  non-answer attached instead of an untested assumption. `best_idx = max(observed_sharpe)` stands
  because it was tested, which is a different state from standing because nobody looked.
- Every published number is unchanged; nothing on disk moved.
- The next selection experiment inherits a working two-arm harness and a criterion-writing rule that
  two failures paid for.

## How to reverse

Nothing to reverse — this ADR changes no code. To revisit, dispatch both arms at n ≈ 400 and state
the criterion on the aggregate with its standard error computed first.
