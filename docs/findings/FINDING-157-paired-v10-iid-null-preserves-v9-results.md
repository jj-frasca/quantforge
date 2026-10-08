# FINDING-157: Current v10 iid null cohort preserves the paired v9 results

- **Date:** 2026-10-07 (completed 2026-10-08 UTC)
- **Severity:** Informational — bounded local calibration evidence
- **Status:** Complete for this fixed cohort; bootstrap and power remain separate
- **Governing decisions:** ADR-018, ADR-036/037, ADR-044/047/048/051/063/209

## Result and paired comparison

The frozen current-v10 cohort completed all **200 symbols with zero errors,
zero graduates and zero ADR-018 survivors**. The sources are byte-identical to
F156's historical v9 cohort. Every result field, including all 200 per-symbol
diagnostics, is exactly equal across the two results except
`search_config_version`. No diagnostic symbol changed.

This is evidence that the numerical repairs preserve these ordinary-scale
search results. It does not establish equivalence for other input geometry,
subnormal returns, different seeds, another null model or real markets.

| Component | v9 passing / 200 | v10 passing / 200 |
|---|---:|---:|
| DSR | 0 | 0 |
| PBO | 180 | 180 |
| Stability | 53 | 53 |
| MinTRL | 15 | 15 |
| Positive holdout Sharpe | 118 | 118 |
| Beat buy-and-hold | 29 | 29 |
| Composite graduation | 0 | 0 |
| ADR-018 survival | 0 | 0 |

These are **200 paired sources measured under two procedures**, not 400
independent observations. Each version's one-sided exact 95% binomial
zero-event upper limit is `1 - 0.05**(1/200) = 0.014867039231272057` (about
1.49%), conditional on the fixed iid-symbol model. Pairing does not tighten
that bound by doubling the sample size. Marginal component counts are not
independent probabilities; graduation was checked as the per-symbol conjunction.

## Frozen current-version procedure

- Executed revision: `380df9826da9f3a01be971537b6ede40e7903e68`.
- Accounting: `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`.
- Search: `969dd54dd031779c97940ffbc94ebcb47a0d6dee0d66ef2a5b225abf8b6b8893`.
- Gate: `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
- Sources: unchanged `iid_normal_null`, `NULL0000` through `NULL0199`, seeds
  `20261007 + global_index`, 7,400 bars, drift 0.0003, vol 0.012, start price
  100. This null has no predictive serial edge beyond drift and its benchmark;
  it is not a zero-mean-return experiment.
- All 34 catalog families, `n_per_param=3`, default `GateConfig()` (trial budget
  200), adaptive refinement on, span 0.25, observed finalist selection.
- Every holdout has 1,480 bars, or 1,480/252 trading years. Independently computed
  universe bar: `sqrt(2*ln(200)/(1480/252)) = 1.34323931596704`.
- Python 3.12.13, NumPy 2.4.6, pandas 3.0.3, SciPy 1.17.1; default NumPy error
  state. Elapsed time 2,424.529 seconds. The plan and source digest preceded
  search; a neutral 9,000-second timeout would invalidate completion.

The process loaded its functions at the stated revision. Subsequent test-only
and documentation commits did not change the generator, search or gate. The
v9 execution identity remains F156's `f1891104...`; it was not relabeled v10.

## Evidence and independent audit

Current scratch artifacts are in `/tmp/qf-s15-null-v10`: `plan.json`,
`source_digest.txt`, `result.json`, `summary.json`, `audit.json` and
`paired_comparison.json`. Driver: `/tmp/qf-s15-null-paired-attack.py`; log:
`/tmp/qf-s15-null-paired-attack.log`. Scratch retention is not guaranteed.

- Paired source SHA-256: `0c19416d6a61e3cc95e72b1fc191cbab26641cddd5e68d655d2e99e39f5e8da6`.
- Current result SHA-256: `c41ebc17f0e07abb766be9a3006fc1d788a4bd251737e404e9d1a019cfbfd027`.
- Historical result SHA-256: `6cfa4d8c8dbc614e7fe503d9c18fb172d2fb58003b7bad8e28e9a7c264eb3792`.

The independent JSON audit uses no production gate or universe helpers. It
checks both complete ordered cohorts, zero errors, every holdout length,
plan/result identities, all six gate booleans and their conjunction, graduate
and survivor projections, and the independently calculated universe bar. It
then compares every diagnostic and the entire result payload after removing
only the top-level search identity. A separate research review checks the
recorded evidence and inference limits.

The recorded maximum trial DSR margin remains -0.4546876217639284, as in v9.
Finalist-only diagnostics cannot independently reconstruct that across-trial
maximum; it is a production summary statistic, not independently audited
trial-level evidence.

## Limits and next controls

No source, seed, selector, budget or threshold changed in response to results.
Generated project data remains untouched. This offline measurement does not
replace sole-writer cloud artifacts or populate the dashboard.

The separately frozen AR(1) power cells at phi -0.3 and +0.3 and the Student-t
df5 null stress need their own completed-cohort reports; their rates must not
be pooled here. No eligible raw SPY OHLCV cache exists in this isolated
worktree. Research-pool experiments and aggregate bootstrap summaries cannot
substitute for source bars, so SPY bootstrap calibration remains unavailable
under the no-provider/no-cloud scope. This Gaussian measurement does not
authorize a gate change or certify market false-positive control.
