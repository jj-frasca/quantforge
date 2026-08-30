# ADR-069: Make the finalist selection rule a measured choice

- **Status**: Accepted (the parameter and the sweep; the DEFAULT does not change here)
- **Date**: 2026-08-30
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Acts on**: ADR-060 (family selection is not separable from the runner-up), ADR-038 (walk-forward
  as a prequential view of the SELECTION procedure), ADR-044/052 (fingerprint the procedure)
- **Relates to**: ADR-063 (how to phrase a pre-stated criterion), ADR-068 (drift in the OOS statistic)

## Context

`run_search` picks the finalist family by **in-sample observed Sharpe**:

```python
best_idx = max(range(len(trials)), key=lambda i: trials[i].observed_sharpe)
```

Every measurement since ADR-057 has pointed at that line, and nothing has ever tested it:

- **ADR-057/059**: on a process that is *by construction* fast mean reversion, the search picks a
  **Trend** strategy 68% of the time, and the headline capture is carried by trend strategies
  fitting the level rather than by the strategies designed for the process.
- **ADR-060**: on real symbols the family the search picks leads the runner-up by **+0.079 Sharpe
  against a standard error of ≈0.22** — a third of one standard error. The selection is choosing
  between families it cannot distinguish.
- **ADR-063**: capture fell when 1,600 bars were added, precisely because the numerator is an
  in-sample maximum over the searched grid and more data regresses it toward what it estimates.
  *An in-sample argmax is a biased estimate of the thing it is being used to rank.*
- **ADR-038** already computes, per family, the statistic that ranks the **selection procedure**
  rather than its luckiest draw: the mean out-of-sample Sharpe of re-selecting on each expanding
  train block and scoring on the next. It is recorded on every `Trial` and is used for nothing.

`walk_forward_oos_sharpe` is computed on the in-sample handle only. Selecting on it therefore
**does not touch the sealed holdout** (ADR-016) and is not leakage; it is ordinary prequential model
selection. So the project has, sitting on every trial, a plausibly better ranking key than the one
it uses, and has never measured the difference.

**The standing target of this research programme is the selection step.** It is not "add another
strategy" — ADR-056/058 tried that and removed it again.

## Decision

**Make the selection rule an explicit, fingerprinted parameter, measure both arms with the power
machinery already built, and change nothing else until that measurement says to.**

1. `run_search(..., select_by="observed" | "walk_forward")`. `"walk_forward"` ranks families by
   `walk_forward_oos_sharpe`, falling back to `observed_sharpe` for a family that has none — a
   family with no walk-forward number must not be ranked as if it scored zero (ADR-067).
2. **The default stays `"observed"`.** This ADR buys the ability to answer the question; it does not
   answer it. Switching the default is a separate decision on the evidence below.
3. `calibration_search_version` includes the rule **only when it is not the default**, so the
   fingerprint of every experiment and null artifact already on disk is unchanged and ADR-064's
   matched comparison keeps working. A non-default rule is a different procedure and gets a
   different fingerprint, which is exactly what ADR-044 requires.
4. `measure_power` and the power driver/workflow take the flag, so the two arms are measured by the
   same code path on the same planted processes at the same lengths.

### The criterion, stated before the run

ADR-063's failed criterion taught the rule: **phrase it over the cells where the achievable oracle
exceeds the requirement, never over raw outcomes.** At `n_bars = 7400` the AR(1) cells with an edge
to find are φ = −0.3, −0.2, +0.2, +0.3 (detection 40 / 36 / 24 / 66%); φ = ±0.1 is where ADR-055
found no achievable edge at all and is excluded from the criterion by construction.

**Switch the default to `walk_forward` only if, at the same seeds and lengths:**
- detection **rises in at least one** of those four cells and **falls in none**, and
- the null's false-graduation rate stays at **0/200 on both nulls**, and
- the change is argued in its own ADR that records both arms' numbers side by side.

Anything else — including "it selects a more sensible-looking strategy" — leaves the default alone.
A selection rule that picks the category a human would have picked, without detecting more planted
edge, has improved a narrative and nothing else.

### Amendment made during implementation

**The non-default arm is not committed.** Both calibration workflows take a `select_by` input and
skip their commit step unless it is `observed`. Two reasons, and they are the same reason twice:
`null_artifact_name` names an artifact by mode and history but not by selection rule, so a
`walk_forward` run would overwrite the published null with a measurement of a *different procedure*
— the ADR-065 failure on a new axis; and the dashboard's power panel keys its tables on `edge`, so a
second `ar1` sweep would render as two identical-looking tables a reader cannot tell apart. The
non-default arm lives in its run artifact and Slack, and the ADR that decides the switch cites the
run id. If the rule ever becomes a standing published dimension, name the artifacts for it first —
ADR-065's argument applies unchanged.

## Alternatives considered

- **Just switch it.** Rejected: it changes what every future experiment means, invalidates the
  fingerprint that makes ADR-064's comparison possible, and would be adopted on a plausibility
  argument in a project whose whole value is that plausibility arguments are measured.
- **Select by deflated Sharpe.** Already the tie-break in `_finalist` and it is still an in-sample
  quantity with a multiple-testing haircut — it corrects for how many hypotheses were tried, not for
  the optimism of the maximum itself.
- **Select by purged-CV OOS Sharpe.** Its folds are not causal (a fold trains on rows after its own
  test block), so ranking a *selection procedure* by it scores a procedure nobody can run forward.
  ADR-039 keeps it as a leakage-controlled dispersion diagnostic; that is the right use.
- **Select by walk-forward excess over buy-and-hold (ADR-068).** Attractive — it is the
  drift-controlled version of the same key — but it needs a benchmark that no artifact carries yet,
  and adding a second untested variable to the first measurement of the first one is how a sweep
  stops answering anything. Measure `walk_forward` first; excess selection is the obvious follow-up.
- **Ensemble the top families instead of picking one.** A different and larger decision (it changes
  what a graduate *is*), and it should be argued after the ranking key is settled, not instead of it.

## Consequences

- Two arms of the power sweep become comparable by construction, because they run the same code.
- The pool, the nulls and every published number are untouched while the default is `"observed"`.
- A `walk_forward` run writes experiments with a different `search_config_version`, which
  `compare_with_null` will correctly refuse to pool with the existing ones. That refusal is the
  mechanism working; it is also why this must never be enabled on the production discovery workflow
  before the switch decision is made.
- Ranking by a mean over five walk-forward windows is noisier per family than an in-sample maximum.
  If detection falls, that is the honest result and is what the criterion is for.

## How to reverse

Drop the parameter and its fingerprint key. Every artifact written under the default is bit-identical
either way, which is the property that makes this safe to add.
