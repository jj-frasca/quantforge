# ADR-034: Meta-labeling is declined — there is no primary edge worth filtering yet

- **Status**: Accepted (resolves the "Proposed" half of ADR-028)
- **Date**: 2026-08-18
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Supersedes**: ADR-028 §Decision, "Proposed (NOT built without Joe's blessing) — meta-labeling"

## Context
ADR-028 recorded meta-labeling (López de Prado 2017) as the next frontier, pending a decision on
taking an ML dependency. The charter hands that decision to the autonomous session: *"build it
(needs an ML dep + its own ADR + a purged-CV protocol) or drop it."*

Meta-labeling is a **secondary** model. It takes a primary strategy's signal as given and predicts
whether to act on it and how big — it separates side from size. Its entire value proposition is
conditional on the primary signal having an edge worth filtering.

Measured on the live research pool today (2026-08-18):

```
symbols in pool                      607
graduate experiments                 206
leaderboard graduates (best/symbol)   40
     ... clearing the ADR-018 universe-deflation bar:   0
```

Zero. The best is `CASY rsi_mean_reversion` at a 1.64 holdout Sharpe against a 1.73 bar. Not one
primary signal in the catalog is currently distinguishable from best-of-N selection luck across the
universe, and the paper book built from that population is −5.4% since inception (ADR-033).

## Decision
**Do not build meta-labeling. Do not add an ML dependency.**

The precondition for revisiting is explicit and measurable: **at least one primary graduate clears
the ADR-018 universe-deflation bar, and holds up over ≥126 forward bars in the paper book.** When
there is a signal we actually believe, filtering it is a sensible next step. Until then it is
sophistication applied to noise.

## Why now rather than later

Building it now would be actively harmful, not merely premature:

- **It inflates the trial count against ourselves.** Feature sets, barrier widths, horizons and
  classifier hyperparameters are all searched. Every one of those trials enters the DSR/MinTRL
  denominator and raises the bar for *everything else in the pool*. Spending that budget on the
  most overfitting-prone technique available, in order to filter signals that already fail the bar,
  is the worst available trade.
- **It is the technique most likely to produce a false positive here.** A classifier fitted on
  ~4 years of holdout across 607 names will find *something*. ADR-028 already flagged it as
  overfitting-prone and demanded a purged-CV protocol first — that protocol only has meaning as a
  defence for a hypothesis worth defending.
- **The dependency is the smallest part of the cost.** scikit-learn is free and installs in
  seconds. The real cost is a `research/ml/` tree, a labelling scheme, a CV protocol, and the
  permanent obligation to keep all of it honest — an obligation that pays nothing until there is a
  primary edge.

## Alternatives considered

- **Build it with a numpy logistic regression to stay dependency-free.** Rejected: the dependency
  was never the objection. Hand-rolling the classifier would make the implementation *worse* and
  the validation burden identical.
- **Build a minimal prototype to "see if it helps".** Rejected — this is precisely the shape of
  research that manufactures results. A prototype with no pre-registered success criterion, run
  against a pool with no surviving primary edge, can only produce an encouraging-looking number.
- **Build it and exclude its trials from the MinTRL denominator.** Rejected outright: that is
  weakening the gate to accommodate a technique, which charter §4 forbids without qualification.
- **Defer silently and leave ADR-028 "Proposed".** Rejected: an unresolved proposal is a standing
  invitation for a future session to re-litigate it from scratch. Deciding "no, and here is exactly
  what would change that" costs one document and saves that session.

## Consequences

- No new dependency, no `research/ml/` tree, and the DSR/MinTRL denominator stays spent on primary
  signal search — where the pool currently has nothing to show for itself.
- The stated precondition makes this trivially reversible and non-arbitrary: it is checked by the
  same `survives_universe_deflation` field ADR-033 now records on every position, so a future
  session does not need to re-derive the question, only re-read the number.
- ADR-028's accepted half is unaffected and already built: `xs_alpha34`, `xs_alpha19` and
  `xs_composite` are live in the cross-sectional registry.

## Reversal
Reopen when the precondition is met. Nothing was built, so there is nothing to unwind — reversing
this decision costs only the ADR that supersedes it.
