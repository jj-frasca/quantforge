# FINDING-156: Fixed v9 iid null cohort graduates zero of 200 symbols

- **Date:** 2026-10-07 (run completed 2026-10-08 UTC)
- **Severity:** Informational — bounded local calibration evidence
- **Status:** Complete at v9; historical control, not v10 certification
- **Governing decisions:** ADR-018, ADR-036/037, ADR-044/047/048/051/063

## Result

One fixed cohort of 200 independently seeded iid-normal symbols, each with 7,400
bars, completed the unmodified full-catalog search and incumbent gate with **zero
errors, zero graduates, and zero ADR-018 survivors**. Every source symbol has a
complete ordered diagnostic and a 1,480-bar holdout (1,480/252 trading years).
The independently recomputed universe-deflation bar is 1.34323931596704.

| Component | Finalists passing / 200 |
|---|---:|
| DSR | 0 |
| PBO | 180 |
| Stability | 53 |
| MinTRL | 15 |
| Positive holdout Sharpe | 118 |
| Beat buy-and-hold | 29 |

These are marginal component counts, not independent probabilities. Composite
passage is the conjunction on each symbol; every finalist fails DSR. The maximum
recorded deflated-Sharpe margin across all search trials is -0.4546876217639284,
as recorded by the production aggregator. That maximum cannot be independently
reconstructed from the summary's finalist-only diagnostics and is not presented
as separately audited trial-level evidence.

Zero observed events do not imply a population error rate of zero. Under this
fixed iid-symbol model, the one-sided exact 95% binomial upper limit for the
whole-pipeline false-graduation probability is
`1 - 0.05**(1/200) = 0.014867039231272057` (about 1.49%). This is a bounded local
measurement, not a guarantee for bootstrap, heavy tails, dependent market panels,
or another search/gate version. Power was not measured by this null cohort.

## Frozen procedure and identity

- Executed revision: `f1891104cc7e90b2d18dc69e78251d61e38253c1`.
- Accounting: `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-v9`.
- Search: `275d6a94ae4cc8c53260928ccfd69e7f191f507db125258b2de8246692389bb3`.
- Gate: `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
- Symbols: `NULL0000` through `NULL0199`, in that order.
- Seed: `20261007 + global_index`, with all 200 sources materialized before search.
- Generator: unchanged `iid_normal_null`, drift 0.0003, vol 0.012, start price 100.
  Positive drift remains: the null lacks predictive serial edge beyond drift and
  its benchmark; it is not a zero-mean-return experiment.
- All 34 catalog families, `n_per_param=3`, default `GateConfig()` (trial budget
  200), adaptive refinement on, span 0.25, observed finalist selection.
- Python 3.12.13, NumPy 2.4.6, pandas 3.0.3, SciPy 1.17.1; default NumPy error
  state recorded. No parameter, seed, budget, selector or threshold changed after
  outcomes. A neutral 9,000-second timeout would have invalidated completion.
- Elapsed time: 2,225.958 seconds. Only mapping iteration emitted progress; the
  generator, search and gate were unchanged.

ADR-209 subsequently advanced the procedure to v10. This already-running process
retained its loaded v9 functions and identity; its result must not be relabeled
as v10. A separately preregistered paired v10 cohort uses identical source bytes.
No paired result or current-version error-rate conclusion is asserted here.

## Evidence and independent audit

Scratch artifacts reside in `/tmp/qf-s15-null-v9` (not generated project data):
`plan.json`, `source_digest.txt`, `result.json`, `summary.json`, and `audit.json`.
The original driver is `/tmp/qf-s15-null-attack.py`; its progress log is
`/tmp/qf-s15-null-attack.log`. Scratch retention is local and not guaranteed.

- Source SHA-256: `0c19416d6a61e3cc95e72b1fc191cbab26641cddd5e68d655d2e99e39f5e8da6`.
  Ordered symbol bytes, little-endian int64 index nanoseconds and little-endian
  float64 OHLCV values in generator column order were hashed before search.
- Canonical result SHA-256: `6cfa4d8c8dbc614e7fe503d9c18fb172d2fb58003b7bad8e28e9a7c264eb3792`.
- Independent JSON audit checks all 200 ordered symbols, source/holdout lengths,
  plan/result hashes, zero errors, every gate conjunction, graduate identities,
  and survival/count projections. It recomputes `sqrt(2*ln(200)/(1480/252))`
  directly without the project's universe helper.

At the pinned revision, the core reproduction is:

```python
frames = {f"NULL{i:04d}": iid_normal_null(7400, seed=20261007 + i) for i in range(200)}
names = [entry.name for entry in STRATEGY_CATALOG]
result = calibrate_gate(
    frames, names, config=GateConfig(), n_per_param=3,
    refine=True, refine_span=0.25, null_mode="iid_normal", select_by="observed",
)
```

## Limits and next controls

This scratch measurement does not replace sole-writer cloud artifacts, populate
the dashboard, or authorize a gate change. Generated `data/*.json` remains
untouched. No vendor API, key, paid runner, workflow dispatch or cloud resource
was used. Code pushes used the ordinary required CI.

Complete the fixed paired v10 cohort, then read its exact identity and all errors
before comparison. Frozen 200-symbol controls at phi -0.3 and +0.3 are separate
power cells; never pool their rates. F155 requires calling their existing oracle
outputs the historical reference sign strategy, not a conditional-mean optimum.
Bootstrap and other null modes remain unmeasured in this local experiment.
