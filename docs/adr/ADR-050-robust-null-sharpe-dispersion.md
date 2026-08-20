# ADR-050: Estimate DSR's null trial dispersion robustly

- **Status**: Accepted
- **Date**: 2026-08-20
- **Deciders**: Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Extends**: ADR-046 (whole-search trial accounting), ADR-049 (power attribution)
- **Finding**: `docs/findings/FINDING-006-dsr-dispersion-is-signal-contaminated.md`

## Context

ADR-046 correctly prices every evaluated configuration and the final cross-family selection, but
estimates the expected-null maximum with the sample standard deviation of all current candidate
Sharpes. The primary Bailey/López de Prado formulation uses variance across trial Sharpe estimates;
it also assumes those trials form an approximately Normal strategy class under the null. QuantForge
pools heterogeneous families, and under an alternative their unequal exposure to a real edge
becomes contamination of the null scale.

The production-parity power sweep measured the consequence: DSR passed 0/50 in all 12 planted-edge
cells. In a matched seed, standard deviation rose from 0.510 on iid noise to 1.703 at AR(1)
`phi=+0.30`, producing a 4.698 haircut against observed Sharpe 2.937. The edge raises its own null
bar faster than the finalist can clear it.

A 10-seed local comparison applied an IQR-based Normal scale to the same full-catalog, 200-budget,
refined searches. All 10 iid-null finalist margins remained negative. Nine of 10 strong-edge DSR
margins became positive, and three passed the unchanged composite gate. This is preliminary
mechanism evidence; production claims still require the full ADR-036/041/042 cloud calibration.

## Decision

Estimate whole-search cross-trial Sharpe dispersion as

```
sigma_null = max((Q75 - Q25) / (Phi^-1(0.75) - Phi^-1(0.25)), 1e-6)
```

for trial families of at least four candidates. Two- and three-candidate families retain sample
standard deviation because interpolated quartiles are biased low at those sizes. Family-local
reports remain unchanged; production's longitudinal and cross-sectional finalists are subsequently
repriced by the shared whole-search path this ADR repairs.

The denominator makes the estimator consistent for the Normal trial distribution assumed by the
paper. The central 50% has a 25% contamination breakdown point, so a minority of strategies that
genuinely load on an edge cannot inflate the supposed null scale without bound. It still estimates
dispersion from the complete current trial family, preserves one common cross-family haircut, and
uses the unchanged cumulative lifetime trial count. Degenerate families retain the existing
positive floor.

Version this estimator in calibration search identity. Re-run iid/bootstrap Type-I calibration and
both planted-edge power sweeps before describing the new procedure as production-calibrated. Change
no gate threshold, trial count, candidate budget, holdout, PBO, stability, MinTRL, beat-buy-and-hold,
or universe-deflation rule.

## Alternatives considered

1. **Keep sample standard deviation.** Rejected by measured zero power and its unbounded response to
   signal-contaminated tails.
2. **Hard-code a dispersion from the latest null artifact.** Rejected: the artifact does not yet
   preserve candidate dispersion, and one scalar would silently drift across sample lengths,
   catalogs, and cross-sectional searches.
3. **Use MAD.** Robust, but the catalog produces a large mass of exactly flat/zero-Sharpe configs;
   median-centered absolute deviations can collapse or become unstable. The IQR uses more of the
   central distribution and matched the iid standard deviation in the deterministic reproduction.
4. **Adopt the paper's probability-form DSR now.** Rejected in this decision because it changes the
   metric domain and `dsr_min` semantics. FINDING-007 records that separate source mismatch; it must
   not be hidden inside a dispersion repair.
5. **Restore family-local pricing.** Rejected: it would reintroduce FINDING-002 by omitting the
   cross-family argmax and lifetime search effort.

## Consequences

- The multiple-testing price remains conservative and lifetime-counted, but a few extreme trial
  Sharpes can no longer make the null scale arbitrarily large.
- Null and power calibration identity changes, so stale artifacts are detectable and their prior
  measurements remain evidence only for the standard-deviation procedure.
- Full cloud calibration is the acceptance evidence. A red Type-I result requires reverting or a
  new ADR, never moving `dsr_min`.

## Reversal

Restore sample standard deviation in family-local and whole-search pricing and restore the previous
trial-accounting version. This intentionally restores FINDING-006's measured zero-power behavior.
