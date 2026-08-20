# ADR-054: Compute the paper's Deflated Sharpe Ratio, and stop calling the margin by its name

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Autonomous session (authority delegated by Joe, `.claude/AUTONOMY_CHARTER.md` §1)
- **Resolves**: `docs/findings/FINDING-007-dsr-field-is-not-paper-probability.md` (open, High)
- **Extends**: ADR-016 (graduation gate), ADR-046 (whole-search trial accounting), ADR-050 (robust dispersion)
- **Relates to**: ADR-018 (universe deflation), ADR-036/041/051 (calibration)

## Context

FINDING-007 is correct and it is the most serious open item in the repository, because it is about
the one thing this project claims: that its numbers are what they say they are.

Bailey and López de Prado (2014) define the Deflated Sharpe Ratio as a **probability** — a
Probabilistic Sharpe Ratio evaluated against a multiple-testing-adjusted threshold, using the
selected strategy's sample length, skewness and kurtosis as well as the number and variance of
trials. `app/validation/deflated_sharpe.py` computes `observed_sharpe - expected_max_sharpe`. That
is a useful selection-adjusted **margin**, and it is not the paper's statistic. It omits the sample
length and the non-Normal-return correction entirely, and it lives on a different scale: the paper's
DSR is in [0, 1], the margin is in Sharpe units.

The repository documents the divergence as a "value form" in one place and then cites the primary
paper by name in the API, the dashboard, the README and five ADRs. A reader who knows the paper
will assume the probability. A reader who does not will believe the citation.

Two facts make this fixable now rather than later. First, the omitted inputs are all available at
the point of computation: `whole_search_deflated_sharpes` already holds the candidate Sharpes and
the return series is in hand. Second, all three calibration workflows now measure at production
parity and at a matched history length (ADR-051), so a change to the statistic can be answered with
a measured Type-I error and a measured power curve within the hour instead of argued.

## Decision

**Implement the paper's probability-form DSR, record it beside the margin, and correct every claim
that calls the margin by the paper's name — but do not change what the gate gates on in this ADR.**

1. `probabilistic_sharpe_ratio(observed_sr, benchmark_sr, n_returns, skew, kurtosis)` — PSR as
   published, the Normal CDF of the standardized excess over a benchmark Sharpe, with the
   non-Normality correction in the denominator.
2. `deflated_sharpe_probability(...)` — PSR evaluated against `expected_max_sharpe(n_trials, sr_std)`
   as the benchmark, i.e. the paper's Equation 2 using this repo's existing, calibrated haircut.
3. `Trial.deflated_sharpe_probability`, recorded alongside the existing margin. Nullable, so the
   3,237 pool rows that predate it read as unmeasured rather than as a probability of zero.
   The trap is scale: everything stored in a `Trial` is annualized, while PSR is a function of the
   *per-period* Sharpe and the *per-period* moments together. Mixing one annualized input with two
   per-period ones silently rescales the probability, which is precisely the class of error this
   ADR exists to remove. Implemented by de-annualizing the observed Sharpe AND the trial dispersion
   by the same `sqrt(252)` inside `whole_search_deflated_sharpe_probabilities`, and by returning the
   finalist's `ReturnMoments` (raw kurtosis) from `_score_configs`, which is the only place the
   finalist's return series exists. A finalist whose moments are absent, or whose moment combination
   the formula refuses, records `None`: one unmeasurable family must neither fabricate a number nor
   abort a hunt.
4. The existing field keeps its stored name and the gate keeps its `dsr_min` threshold. What changes
   is the language around it: it is described everywhere as the **selection-adjusted Sharpe margin**,
   and "Deflated Sharpe Ratio" refers only to the probability.

## Alternatives considered

- **Rename the stored field too (`deflated_sharpe` → `selection_adjusted_sharpe_margin`).** Rejected
  for now. It is a schema migration across 3,237 committed pool files, a paper book, the API
  response, four Zod schemas and the dashboard, in service of a name — while the honesty defect is
  entirely in what the name *claims*, which prose and labels fix at zero risk. Recorded as the
  obvious follow-up if the probability form later replaces the margin outright.
- **Switch the gate to `probability > p` in this ADR.** Rejected, and this is the important
  restraint. It is a threshold change, and charter §4 forbids arguing one without evidence.
  Recording the probability first means the switch can be proposed later with a measured Type-I
  error, a measured power curve, and the two statistics' disagreement rate on the same trials —
  which is a much stronger case than any argument available today.
- **Delete the margin and report only the probability.** Rejected: the margin is what every existing
  calibration result, the ADR-018 deflation bar, and the whole committed pool are expressed in.
  Removing it would invalidate the measured record this project's value rests on.
- **Do nothing but rename (FINDING-007's option 2).** Rejected as the weaker half of the fix. The
  finding offers it as an alternative to implementing the statistic; implementing it costs one
  tested function and gains the sample-length and non-Normality corrections the margin lacks.

## Consequences

- Every new trial carries both numbers, so the disagreement between them is measurable rather than
  hypothetical. That measurement is the precondition for any future gate change. Rows already in
  the pool carry `None` and are distinguishable from a measured zero.
- The probability is scale-free and comparable to the literature, which the margin is not.
- Nothing gates on the new field, so no calibration result is invalidated by this ADR and the
  committed Type-I and power measurements remain current. **This is deliberate**: had the gate
  changed, ADR-051's matched Type-I and power runs would have needed re-dispatching in the same
  commit to avoid publishing stale error rates.
- The kurtosis convention must be stated and tested, because the PSR denominator is written with
  raw (not excess) kurtosis and a Normal series must reduce to the familiar `sqrt(n-1)` form.

## Reversal

Delete the two functions, their tests, and `Trial.deflated_sharpe_probability` (nullable, so rows
written under this ADR still load), and revert the wording changes. The gate, the stored margin, the
deflation bar and every calibration artifact are untouched by all of it.
