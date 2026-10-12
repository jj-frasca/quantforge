# FINDING-208: Unpriced signal names remove neutral portfolio legs

- **Status:** Corrected — ADR-259 refuses unpriced names before ranking
- **Date:** 2026-10-12
- **Severity:** High — directional returns published under a neutral claim
- **Scope:** Public cross-sectional portfolio_returns signal/price membership
- **Decision:** ADR-259

## Evidence

Prices A=[100,110,121], B=[100,100,100]; signals A=1, B=2, UNPRICED=3 on every
row; quantile=0.5 and zero cost. Original ranking gives A=-1, B=0, UNPRICED=+1.
Projection onto price columns drops the long leg. Net exposure is -1 on every
row; returned net is [0,-0.10000000000000009,-0.10000000000000009]. Changing the
unpriced name to the lowest rank analogously removes the short leg.

ADR-024 promises equal unit long/short legs; ADR-025 explicitly warns that market
drift through imperfect neutrality can yield apparent factor Sharpe. ADR-138/140
bind production universe evidence, and standard signal generators retain price
columns. Independent research-expert review reproduced the public defect and
approved refusal before ranking while preserving sparse/subset/reordered inputs.
No historical production, calibration, graduate or broker contamination is inferred.

## Correction and required evidence

Refuse signal columns absent from prices before ranking. Do not silently project
and rerank, normalize identities, demand complete signal panels or change tie order.
Preserve original valid frames/formulas and NaN warmup. Observe RED, independently
verify exact native compatibility, then run the full foreground gate before shipping.

## Observed verification

Pre-implementation tests recorded 11 failures and eight preserved cases. The
two-line membership guard made 302 affected engine/ranker/forward/search tests
pass. Independent final review approved 121 engine tests, 105 exact native,
sparse/subset/reordered/warmup/empty baseline comparisons, and 45 configurations
across all 16 standard generators. Extra keys in static score maps remain excluded
by those generators. Refusal occurs before ranking, with original cost-validation
precedence retained. The initial full gate stopped at three test regex lint
errors; raw-string notation corrected them without changing assertions or source.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,218 backend tests
at 97.75% coverage and 363 frontend tests at 97.63% statement coverage; lint,
formatting and type checks passed.
