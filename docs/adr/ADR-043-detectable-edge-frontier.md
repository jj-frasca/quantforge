# ADR-043: Compute the detectable-edge frontier, and design the search against it

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Extends**: ADR-018 (universe deflation), ADR-041 (power calibration)
- **Relates to**: ADR-029 (fundamental pre-screen), ADR-036/037 (null calibration), ADR-042

## Context
ADR-041 measured the gate's power against a planted edge and found it usable only for oracle
Sharpe ≳ 2.5, with **0 of 50 detected** at oracle ≈ 1.3 in either direction. That is a measurement
of the whole pipeline — search, DSR, PBO, MinTRL, holdout, and the ADR-018 deflation bar together —
and it leaves the obvious design question unanswered: **how much of that is statistics and how much
is the catalog?**

The two have completely different remedies. If the pipeline's *statistical* resolution is the
binding constraint, no amount of better strategies helps and the fix is in the experiment's design
— how many hypotheses are tested, and over how much held-out data. If instead the statistics permit
detecting a Sharpe-1.5 edge and the catalog still misses it, the catalog is the problem.

The pieces to separate them already exist in the repository and have never been put together.
`expected_max_sharpe_under_null(n_symbols, holdout_years)` gives the bar a graduate must clear. Lo
(2002) gives the sampling distribution of an estimated Sharpe. Together they answer: **what true
Sharpe must an edge have for this pipeline to detect it at a stated probability?**

## Decision
**Add `app/research/lab/frontier.py`: the minimum true annualized Sharpe an edge must have for the
ADR-018 bar to be cleared with probability `power`, as a function of universe size and holdout
length — and print it in `scripts/pool_report.py` beside the standing "0 of N clear the bar".**

### The calculation
An annualized Sharpe estimated over `T` years of daily data has, under Lo (2002) for iid returns,

```
SE(SR) = sqrt((1 + SR^2 / 504) / T)          # 504 = 2 * 252, from annualizing SR^2/2
```

which at `SR = 0` is exactly the `sqrt(1/T)` the ADR-018 bar already uses — the two are the same
formula evaluated at the null and at the alternative. Detection requires the *estimated* holdout
Sharpe to exceed the bar, so the true Sharpe needed for power `p` solves

```
SR_true = bar(N, T) + z_p * SE(SR_true)
```

which is implicit (the standard error grows with the true Sharpe) and solved by fixed-point
iteration from `SR_true = bar`. It converges in a handful of steps because the `SR^2 / 504` term is
small at any plausible Sharpe.

### What this is and is not
- It is the pipeline's **statistical resolution**: the edge size below which the gate cannot be
  expected to fire even for a strategy that captures the edge *perfectly*. It is an optimistic
  bound in exactly that sense.
- ADR-041/042's measured power is the **realized** number, which is lower. The gap between the two
  is **capture efficiency** — how much of an available edge the catalog actually converts — and
  separating those two quantities is the entire point of computing this.
- It says nothing about whether an edge of that size exists. That is what the hunt is for.

### The design consequence this exposes
The bar scales as `sqrt(2 * ln N)` in the number of hypotheses and as `1 / sqrt(T)` in holdout
length. Those are very different curves, and the asymmetry is the actionable part:

- **Halving the universe barely moves the bar.** 607 → 300 symbols changes `sqrt(2 ln N)` by ~5%.
- **Holdout length is the strong lever.** `1 / sqrt(T)` means doubling the held-out history cuts
  both the bar and the estimation error by ~29%.

This does not make ADR-029's quality pre-screen pointless — testing fewer, better-motivated
hypotheses is right on its own terms, and it is the *honest* way to reduce N (ADR-033) — but it
does say that a session hoping to make the bar reachable by trimming the universe is pulling the
weaker of the two levers by an order of magnitude, and should be told so by the report rather than
discovering it after a week of work.

### What this does NOT license
The frontier is a description of the experiment's resolution. It is **not** an argument for
lowering the bar, and charter §4 stands: if the frontier says the honest detectable edge is Sharpe
2.1 and nothing in the universe has it, the answer is to say so plainly — not to redefine `N`, the
holdout, or the deflation formula until something graduates.

## Alternatives considered
1. **Simulate the frontier instead of computing it.** ADR-041's harness could plant edges of known
   Sharpe and measure detection directly. That is strictly better evidence and it is *already being
   done* — but it measures pipeline power (statistics × capture), which is the product this ADR
   exists to factor. Also ~8 minutes of cloud compute per point versus microseconds, so the closed
   form is what can go in a report that runs on every pool inspection.
2. **Report the bar only, as today.** The bar answers "what must be observed"; it does not answer
   "what must be true", and the difference between those two is the estimation noise that makes a
   Sharpe-1.7 edge fail a 1.7 bar half the time.
3. **Use the Deflated-Sharpe machinery instead.** DSR already deflates for multiple testing within
   a symbol. The universe-level question is across symbols, which is precisely the gap ADR-018 was
   written to fill; reusing DSR here would double-count the within-symbol trials.
4. **Assume normality of returns rather than Lo's correction.** Lo's `SR^2 / 2` term is the
   difference between "the estimator is noisy" and "the estimator is noisier when the true Sharpe
   is large", and dropping it would understate the requirement precisely where it matters — at the
   large effect sizes that are the only ones this pipeline can see.

## Consequences
- `pool_report.py` gains a frontier block, so every future session reads the detectable edge next
  to "0 of 40 clear the bar" instead of re-deriving the interpretation (or not deriving it).
- The frontier is a *statement about the design*, so it changes whenever the universe or the
  holdout policy changes. It is computed from the pool at report time, never stored.

## Reversing this
Delete `app/research/lab/frontier.py`, its tests, and the report block. Nothing gates on it,
nothing is stored, and no threshold is touched.
