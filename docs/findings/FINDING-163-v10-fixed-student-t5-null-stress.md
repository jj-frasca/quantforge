# FINDING-163: Current v10 fixed Student-t5 null stress has no graduates

- **Date:** 2026-10-08
- **Severity:** Informational — bounded heavy-tail calibration evidence
- **Status:** Complete for the frozen 200-symbol cohort
- **Governing decisions:** ADR-018, ADR-036/037, ADR-044/047/048/051/063/209

## Complete result and uncertainty

The entire frozen cohort completed all **200 symbols with zero errors,
zero graduates and zero ADR-018 survivors**. The independent universe bar is
`sqrt(2*ln(200)/(1480/252)) = 1.34323931596704`.

| Component | Passing / 200 |
|---|---:|
| DSR | 0 |
| PBO | 180 |
| Stability | 50 |
| MinTRL | 28 |
| Positive holdout Sharpe | 134 |
| Beat buy-and-hold | 29 |
| Composite graduation | 0 |
| ADR-018 survival | 0 |

Every symbol's six-component conjunction and survivor predicate were checked
independently. Marginal counts are not independent pass probabilities.
For zero graduates, the one-sided exact 95% binomial upper limit is
`1 - 0.05**(1/200) = 0.014867039231272057`, approximately 1.49%, conditional
on the valid-source iid-symbol stress model. This is not proof of zero Type-I
error. The Gaussian null and two planted-edge arms have different laws and
retain their own denominators; pooling them cannot tighten this control's bound.

## Frozen source and procedure

- Executed revision: `8e372d504b007186c980729a4aa581bfb449138b`.
- Accounting: `whole-search-budgeted-robust-iqr-pbo-oos-sharpe-scaled-constant-moments-verified-zero-v10`.
- Search: `969dd54dd031779c97940ffbc94ebcb47a0d6dee0d66ef2a5b225abf8b6b8893`.
- Gate: `250856983fb58b7f0392157eef5c96960a26d0b2b3f81d063281bf6b18eeb493`.
- Null mode: `iid_student_t_df5`; `TNULL0000` through `TNULL0199` in order,
  independent RNG seeds `2026101000 + index`, 7,400 bars per symbol.
  Every holdout contains 1,480 bars, or 1,480/252 trading years.
- Simple returns: `0.0003 + 0.012 * sqrt(3/5) * standard_t(5)` from
  `numpy.random.default_rng(seed)`. Start price 100; closes are the cumulative
  product of `1 + return`. Auxiliary OHLCV draws follow the original null
  construction, continuing that symbol's RNG after returns: open noise 0.012/3,
  high/low absolute noise 0.012/2, volume integers [1,000,000, 5,000,000).
  The original `_ohlcv` construction supplies the unchanged business-day index.
- The scale gives return variance `0.012**2`; raw population kurtosis is 9.
  The law has finite fourth but infinite eighth moments. It has drift, not
  zero expected returns; the benchmark and pipeline costs remain intact.
- All 34 catalog families, default `GateConfig()` with trial budget 200,
  `n_per_param=3`, adaptive refinement on, span 0.25, observed selection.
- Python 3.12.13, NumPy 2.4.6, pandas 3.0.3, SciPy 1.17.1, default NumPy
  error state. Elapsed time: 2773.724 seconds.

The Student-t law is unbounded. The pre-search rule invalidates the **entire
cohort** if any source frame contains invalid/nonpositive prices or malformed
OHLCV; no truncation, redraw, dropping or conditioning-by-replacement is allowed.
All frozen sources passed. Plan and digest preceded search, with a neutral
7,200-second deadline; a timeout would make the evidence incomplete.

This operational restart matches the interrupted session15 plan's sources and
gate/search identities exactly. Plans differ only in start time and executed
revision. No seeds were added, removed or redrawn, and retrying identical
sources adds no observations. Later scalar-validation commits do not retag
the process's loaded revision or change these search outcomes.

## Evidence and independent audit

- Source SHA-256: `449df38ad80afd3393a567dcce2f2cb7dc51fd3220ebcff480c58520c8841db3`.
- Result-byte SHA-256: `947c32b658c23c5847243e362a298c7e286b7c913d20e58e073e9c8c81c618c8`.
- Scratch root: `/tmp/qf-s17-null-t5-v10`, containing plan, source digest,
  result, summary and audit files.
- Driver: `/tmp/qf-s17-t5-attack.py`; count auditor:
  `/tmp/qf-s15-audit-t5.py`; supplementary primitive-evidence auditor:
  `/tmp/qf-s17-audit-supplement.py`. Scratch retention is not guaranteed.

The process exited zero after its final assertions. Independent review rebuilt
all 200 sources without production generator/assembly helpers and matched the
source hash. Separate JSON audits check complete ordered diagnostics/verdicts,
zero errors, exact lengths/identities, strict gate booleans, finite scores and
bounded probabilities, conjunctions, graduate/survivor projections, the
independently calculated bar, summary consistency and result-byte identity.
Current-schema JSON reload passes; independent research review approved the
completed evidence. Full foreground `make check-all PYTEST_WORKERS=4` passed
3,318 backend tests (97.54% coverage) and 359 frontend tests (97.63% statements).

The reported maximum trial DSR margin is −0.27632081311252765. This remains a
production summary: finalist-only diagnostics cannot independently reconstruct
the across-trial maximum. No claim of audited trial-wide evidence is made.

## Limits and next controls

This is one fixed iid heavy-tail stress, not general-market false-positive
certification, a matched historical v9 comparison or a substitute for power.
Infinite eighth moments also preclude treating conventional sample-kurtosis
precision assumptions as established. No threshold, selector, source law,
catalog, identity or generated project data changes in response to outcomes.

SPY bootstrap remains unavailable: this isolated worktree has no eligible raw
OHLCV cache. Pool experiments and aggregate historical bootstrap summaries
cannot substitute for source bars under the no-provider/no-cloud scope.
The cohort does not replace sole-writer artifacts or populate the dashboard,
and authorizes no gate change. F157 and F162 retain their separate evidence.
