# FINDING-162: Current v10 recovers strong fixed AR edges

- **Date:** 2026-10-08
- **Severity:** Informational — bounded offline power evidence
- **Status:** Complete for both fixed 200-symbol arms
- **Governing decisions:** ADR-018, ADR-041, ADR-044/047/048/049/051/063/209

## Complete results

Both frozen arms completed all 200 symbols with zero errors. At phi −0.3,
130/200 graduate and all 130 survive ADR-018. At phi +0.3, 163/200 graduate
and all 163 survive. The independently calculated universe bar is
`sqrt(2*ln(200)/(1480/252)) = 1.34323931596704` in each arm.

| Component passing | AR −0.3 / 200 | AR +0.3 / 200 |
|---|---:|---:|
| DSR | 200 | 176 |
| PBO | 200 | 200 |
| Stability | 130 | 187 |
| MinTRL | 200 | 200 |
| Positive holdout Sharpe | 200 | 200 |
| Beat buy-and-hold | 200 | 200 |
| Composite graduation | 130 | 163 |
| ADR-018 survival | 130 | 163 |

Graduation is the per-symbol conjunction, not a product of marginal rates.
Stability alone rejects the 70 negative-AR nondetections. In the positive arm,
24 fail DSR and 13 fail stability; these failure sets do not overlap.

Conditional on the iid-symbol model, marginal two-sided exact 95%
Clopper–Pearson intervals are 57.9549%–71.5929% for the negative arm's 65%
and 75.4137%–86.6271% for the positive arm's 81.5%. They are not simultaneous
familywise intervals. The arms share innovations: their separate denominators
are 200, and they cannot be pooled as 400 independent observations or used
as an independent directional comparison.

## Reference measurements and attribution

| Median score | AR −0.3 | AR +0.3 |
|---|---:|---:|
| Historical gross sign reference | 3.913557911085787 | 3.9156354779137175 |
| Historical net sign reference | 2.3555906650658436 | 2.848016658881564 |
| Selected finalist observed Sharpe | 2.7023928734692366 | 2.929744039616142 |

FINDING-155 applies: the stored reference is `sign(phi * lagged_return)`;
it omits the generator's drift intercept. These are reference-strategy scores,
not true conditional-mean, cost-aware or realized-sample optima. Finalist observed
scores are selected in-sample maxima and do not certify capture above an optimum.

Negative-arm finalist counts are vwap_reversion 97, overnight_gap 65,
connors_rsi 22, bollinger_bands 11 and mean_reversion 5. Positive-arm counts
are fifty_two_week_high 119, donchian_atr_trail 48, true_strength_index 16,
macd_crossover 10 and triple_ma_alignment 7. These describe selected finalists,
including nondetections, rather than only the successful subset.

## Frozen procedure and provenance

- Executed revision: `8e372d504b007186c980729a4aa581bfb449138b`.
- Accounting: `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`.
- Search: `969dd54dd031779c97940ffbc94ebcb47a0d6dee0d66ef2a5b225abf8b6b8893`.
- Gate: `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
- Unchanged `autocorrelated_edge`: phi −0.3/+0.3, drift 0.0003,
  innovation volatility 0.012, centered initial state zero, start price 100.
  The initialization transient is retained. Each stationary marginal volatility
  is `0.012 / sqrt(1 - 0.3**2)`.
- `EDGE0000` through `EDGE0199`, seeds `2026100800 + index`, 7,400 bars
  per symbol; each holdout has 1,480 bars. Both arms use the same innovation draws.
- All 34 catalog families, default `GateConfig()` with trial budget 200,
  `n_per_param=3`, refinement on, span 0.25, observed finalist selection.
  Net reference turnover costs are 0.001, matching the catalog cost rate.
- Python 3.12.13, NumPy 2.4.6, pandas 3.0.3, SciPy 1.17.1, default NumPy
  error state. Elapsed seconds: negative 2772.726; positive 2791.984.

Plans/source digests preceded search, with neutral 9,000-second deadlines.
These are operational restarts of the interrupted session15 frozen plans.
All sources and gate/search identities match the originals; no seed was
added, dropped or redrawn. Restarting the same cohort adds no observations.
Processes loaded the stated revision; later root-validation/documentation
commits do not retag execution or alter these search outcomes.

| SHA-256 evidence | Negative arm | Positive arm |
|---|---|---|
| Source | `f02b57c75513a9d0742c88f80113a4f9e130454192e12188e2a8f4677af37741` | `23952504f420cb6aa30f53e732cb7855b97da7d8a00663376fca85e250529d3e` |
| Result bytes | `57ec9f9a36988b6b953517f94c39f12cdea9cb9593b5b0892ac77ae005b3d022` | `28946a73ec8b38145b4cdd48bace075a09604496c9a0e7e66d35530c340bcfcd` |

## Independent verification and limits

Scratch roots `/tmp/qf-s17-power-negative-v10` and
`/tmp/qf-s17-power-positive-v10` contain plan, source digest, result,
summary and audit files. Driver: `/tmp/qf-s17-power-attack.py`.
Count auditor: `/tmp/qf-s15-audit-power.py`; supplementary primitive-evidence
auditor: `/tmp/qf-s17-audit-supplement.py`. Scratch retention is not guaranteed.

Both processes exited zero after their final assertions. Independent review
rebuilt all 400 sources without production generators and matched their hashes.
It checked ordered complete verdicts, zero errors, lengths, identities,
strict gate booleans/conjunctions, finite scores/probabilities, counts, summaries
and ADR-018 survivors. All 800 gross/net scalar references exactly match
the independently precomputed source-only reference artifact. Current schema
JSON reload also passes. Independent research review approved the evidence.
Full foreground `make check-all PYTEST_WORKERS=4` passed 3,318 backend
tests (97.54% coverage) and 359 frontend tests (97.63% statements).

This demonstrates recovery of these strong, stationary, always-on synthetic
AR effects under v10. It does not certify weak/intermittent edges, real-market
power, band references, bootstrap calibration or false-positive control.
No threshold, selector, catalog, source, fingerprint or generated project data
changes in response to the outcomes. Student-t and iid-normal nulls retain
their own reports and denominators; these results authorize no gate change.
