# ADR-076: Size ADR-074's window experiment, and spend its second look under a Pocock boundary

- **Status**: Accepted
- **Date**: 2026-08-31
- **Deciders**: Autonomous session #16 (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-074 decision 3, whose criterion was applied once at n = 45 and returned
  inconclusive *by its own pre-stated sizing*
- **Relates to**: ADR-063 (the window change under test), ADR-068 (the drift-controlled statistic),
  ADR-070/074 (state the standard error and the estimator before the threshold), ADR-075 (the
  most recent pre-registration in this family), FINDING-013 (the record this ADR corrects)

## Context

ADR-074 decision 3 pre-stated a criterion — *revisit ADR-063 only if the paired median
drift-controlled excess delta is negative AND its bootstrap 95% CI excludes zero* — and it was
applied on 2026-08-31 at n = 45: **−0.074 [−0.157, +0.030]**. The interval includes zero, the
criterion did not fire, ADR-063's window stayed. ADR-074's own sizing had said in advance that a
null result at that size is inconclusive rather than a pass, and that is exactly what happened: the
half-width was 0.093, about 2.4× the effect being looked for.

ADR-074 then recorded a reason to wait: *"the candidate pool held exactly 45 today and grows as the
discovery records the benchmark on more symbols"*, and told the next session to re-run "when the
candidate pool reaches ~75 symbols."

**That sentence is false, and it is the whole reason this ADR exists.** The candidate set —
symbols carrying `walk_forward_hold_sharpe` at ≥ `WINDOW_SPLIT_BARS` and not below it — held
**368 symbols** at the moment ADR-074 was written, and holds 368 today. `window_experiment.py 45`
took the first 45 of the deterministic shuffle because 45 was the command-line argument, not
because 45 was all there was. The pool's last data commit (`cc2e742`, 2026-08-30) predates that
session, so nothing grew in between; the same script prints `n=4 of 368 paired symbols` today.
FINDING-013 records the error. **The sample size was a free parameter all along, and the experiment
was under-powered by choice rather than by availability.**

Two consequences follow. The re-run should be sized to resolve the effect rather than to reach a
number someone wrote down. And because the first look has already been taken and its point estimate
and direction are known, the re-run is a **second look at a nested sample** — a sequential test, not
a fresh one — and reading it at a nominal 95% interval would inflate the Type-I error the project
claims to control.

## Decision

1. **Freeze the sample before searching any of it.** The n symbols are written to
   `data/window_experiment/adr076_sample.json` and committed **before** the run starts; the driver
   reads that file when it exists instead of re-deriving the sample. This is not a convenience.
   `window_experiment_symbols` shuffles the *current* candidate list, so a pool that grows between
   two invocations silently re-rolls which symbols are in the sample — which would make the
   pre-registration unverifiable and let a resumed run become a different experiment.

2. **n = 200.** Derived from look 1's dispersion, not from a round number. Look 1's bootstrap
   half-width of 0.093 at n = 45 implies SE(median) ≈ 0.0475, hence a per-symbol delta SD of
   σ ≈ 0.254 through SE(median) ≈ 1.253 σ/√n. Against the boundary in decision 3, rejection needs
   |δ| / SE ≥ 2.178, so power against look 1's point estimate of −0.074 is
   Φ(|δ|/SE − 2.178) — **≈87% at n = 200**, ≈79% at n = 169, ≈93% at n = 250. The 45 symbols already
   searched are the deterministic prefix of the sample, so 155 remain to be searched.

3. **The second look is read at the Pocock two-look boundary: nominal two-sided α = 0.0294**
   (bootstrap percentiles **1.47 / 98.53**), which holds the two-look family-wise Type-I at 0.05.
   Look 1 (n = 45) counts as a look; **this is look 2 and it is the last.** The sequence is exactly
   a Pocock design that has not yet rejected — look 1 failed to reject at the *more liberal*
   α = 0.05, so it also fails at 0.0294 — which is what makes the boundary applicable after the
   fact rather than a convenience chosen now.

4. **The estimator does not change.** The statistic stays the median of the within-symbol
   drift-controlled excess delta, with a percentile bootstrap of B = 20,000 at seed 7. ADR-074
   measured that the same 45 deltas give a mean 2.7 SE from zero, which *would* have fired. Moving
   to the mean now that its answer is known is precisely the shopping ADR-070's meta-lesson forbids.
   The 95% interval is still reported beside the boundary interval, labelled as the look-1 estimator
   so the two are never confused.

5. **A partial run is not a look.** The comparison is computed, printed and written only when every
   frozen symbol carries both sides. A run cut off mid-way leaves its shard files on disk and is
   resumed by re-invoking the driver, which skips symbols already searched. **No intermediate
   comparison is printed, quoted or recorded** — reading one and then continuing would be a third
   look that the boundary does not cover.

6. **Sharding is execution, not design.** The frozen sample is split round-robin across K processes
   writing disjoint files (ADR-030: one writer per file). The run is I/O-bound on the price fetch —
   a 4-symbol timing probe cost 12m50s wall against 110s of CPU — so sharding is what makes n = 200
   a two-hour job rather than a nine-hour one. It cannot touch the statistic: the sample is frozen,
   the pairing is within symbol, and the comparison is computed once over the union.

7. **Firing the criterion means revisiting ADR-063, not reverting it.** ADR-063 bought a measured
   reduction in the resolution bar (2.13 → 1.82 as the pool re-searches) and measured detection
   gains in every AR(1) cell with an edge to find. If the boundary interval excludes zero on the
   negative side, that trade is re-argued in its own ADR against both measurements. Nothing reverts
   automatically.

## Full disclosure

- **The direction is known.** Look 1 returned −0.074, and the surrogate reading (−0.038, 95% CI
  excluding zero at n = 368) points the same way. What is pre-registered here is the sample, its
  size, the boundary, and the commitment to report whatever comes back — not ignorance of the sign.
  That is what a group-sequential design is for; it is also why the boundary, not a 95% interval,
  is the honest reading.
- **A 4-symbol timing probe printed a comparison.** Establishing feasibility required running the
  driver, which prints the paired comparison unconditionally; at n = 4 it showed
  −0.107 [−0.346, −0.036]. It is disclosed here rather than discarded. It is **not** a look: n and
  the boundary were both derived from look 1's dispersion before that output existed, the probe's
  four symbols are inside the frozen sample rather than an extra sample, and no decision reads it.
  Decision 5 exists so that this cannot happen again by accident.

## Alternatives considered

1. **Re-run at n = 75, as ADR-074's closing line said.** Rejected: 75 was chosen to make the
   half-width roughly equal to the effect, which is a coin flip (≈50% power), and it was chosen
   under the false belief that candidates were scarce. Spending the last look of a sequential test
   on a coin flip is worse than not spending it.
2. **Re-run at n = 368, the whole candidate set.** ≈99% power and the most decisive option.
   Rejected as the *pre-stated* size because it roughly doubles a run that is already the length of
   an autonomous session, and decision 5 makes an unfinished run worth nothing until it completes.
   n = 200 buys 87% power at a size that can finish. If the boundary interval comes back straddling
   zero, extending to 368 is a **new ADR with a three-look boundary**, not a continuation of this one.
3. **Read the second look at 95%, as look 1 was read.** Rejected: two looks at nominal 0.05 give a
   family-wise Type-I near 0.08. This project's entire claim is that its gate is honest; inflating
   α on the one test that might change a published decision is the cheapest possible way to lose that.
4. **Switch the estimator to the mean.** Rejected under ADR-074's own lesson. The mean is the
   tighter estimator and should have been pre-stated in ADR-074; adopting it now, knowing it fires
   and the median does not, is the failure mode rather than the fix.
5. **Abandon the experiment and let the daily discovery fill in the short window on its own.** It
   never will: `SEARCH_HISTORY_START` is 1990 in production, so the discovery only ever adds
   long-window rows. The short side exists only if this experiment creates it.

## Consequences

- ADR-074's criterion gets one properly-powered reading instead of an indefinite sequence of
  under-powered ones, and the sequence is closed by decision 3 rather than left open.
- The window experiment becomes resumable and shardable, so an autonomous session that is cut off
  mid-run costs nothing but wall-clock.
- The project acquires a worked example of a pre-stated multiplicity correction, which is the
  fourth distinct hole the ADR-063/070/074 series has found in its own criteria — after "the sample
  does not exist", "the SE is larger than the effect", and "the estimator was not pre-stated".
- `data/window_experiment/adr076_sample.json` becomes a committed artifact whose only job is to make
  the pre-registration checkable by a reader who does not trust this file.

## Reversal

Delete `adr076_sample.json` and the ADR-076 shard files, and drop the boundary interval from the
driver's output. ADR-074's n = 45 inconclusive reading is then the last word, which is the state
this ADR found the question in. Nothing else depends on it: no threshold, no gate, no generated
artifact and no graduation decision reads any of it.
