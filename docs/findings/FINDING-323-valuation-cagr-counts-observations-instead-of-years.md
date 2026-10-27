# FINDING-323: Valuation CAGR counts observations instead of fiscal-year intervals

- **Status:** Corrected — ADR-381 fiscal-label-span annualization
- **Date:** 2026-10-27, Codex autonomous session5 (ISO2026-W44)
- **Severity:** Medium — annualized growth and downstream valuation can be overstated
- **Affected:** valuation/intrinsic_value.py:_cagr, estimate_growth and their DCF consumer
- **Related:** ADR-022/381; distinct from ADR-116/117 and FINDING-322

## Evidence before correction

The private helper computes (last / first) ** (1 / (len(values) - 1)) - 1.
estimate_growth supplies line-item observations without their fiscal-year labels.
The canonical history parser sorts present fiscal years but need not return one
observation for every intervening year. Record count is therefore not elapsed
fiscal-year intervals. ADR-116/117 guard other annual comparisons; neither changes
this estimator.

At producing revision c917b706 (source unchanged at 9338fe90), synthetic accepted
CompanyFacts-shaped inputs produce FY2020 and FY2024 cash flows of 100 and 120.
The estimator reports 20% instead of label-span CAGR 1.2 ** (1/4) - 1,
approximately 4.6635%. Default DCF assumptions clamp the erroneous growth to 12%.
With diluted shares of 10 the value per share is 242.8143427580083 rather than
179.70827136679333 using the same endpoint cash flows and native DCF loop.
Adding positive intermediate annual observations with unchanged endpoints also
produces the lower value, showing the dependence on sampling density.

Independent data and research probes use current price 100 and no historical
price observations. The resulting valuation score/margin of safety is
0.5881627136842522 versus 0.4435425857728322 with label-span growth. Parent probe
uses price 10, so its score differs; its growth and DCF values match. Neither price
comparison measures actual mispricing or a gate outcome.

Parent receipt: /tmp/qf-w44-s5-cagr-gap-parent.json. Independent data receipt:
/tmp/qf-w44-s5-cagr-independent-data-engineer.json. The ordinary prepatch baseline
/tmp/qf-w44-s5-cagr-baseline.{py,json} freezes 75 complete consecutive-history
estimator/DCF/valuation claims and the module source. No real vendor acquisition,
production incidence, affected experiment or false graduate is established.

## Decision and limits

ADR-381 uses last fiscal_year minus first fiscal_year as the private helper's
explicit denominator. At the estimator, multi-row labels must strictly increase;
duplicate or descending labels raise ValueError before selecting a series. Empty
and single-row estimates remain None. Native arithmetic for consecutive labels,
observed-series all-present/all-positive eligibility, FCF/net-income/revenue
precedence, clamps, assumptions, flags and the remaining DCF/valuation arithmetic
stay unchanged. Do not infer missing intervening values.

This estimates growth over reported fiscal-year-label intervals. It does not
validate actual observation duration, upstream fiscal-label assignment, economic
consistency or point-in-time availability. F322 remains open. The estimator guard
is not global History validation: DCF can return early for absent/nonpositive base
cash flow or unavailable shares before calling the estimator. No parser, model,
threshold, search, accounting-v14, generated record or frozen cohort changes.

## Verification

Before source edits, the new tests produced 25 expected failures and 13 passing
controls in 0.62 seconds. Initial implementation passed all 38; six subsequent
precedence/clamp/propagation controls bring the new suite to 44. Those six are
postpatch coverage, not additional observed prepatch failures. The Hypothesis
property checks positive observed-series density invariance with fixed labeled
endpoints. A canonical-parser witness and integrated DCF/valuation controls
exercise the actual production functions.

Parent focused verification passed 171 synthetic tests with four live tests
deselected. Independent research ran all 44 new tests; independent data ran
those 44 plus 17 existing valuation tests. Both approved all six paths and
replayed all 75 complete ordinary claims. The scoped whole-module AST comparison
permits only the elapsed-span parameter/exponent, estimator guards/span/call and
two intended docstrings. All other native DCF/estimator source is unchanged.

Logs: /tmp/qf-w44-s5-cagr-{red,green,focused}.log. Foreground make check-all
passed: 15,297 backend tests (97.43% coverage), 746 frontend tests (97.88%
statement coverage), plus lint, formatting and types. Gate log:
/tmp/qf-w44-s5-check381.log. No generated evidence is rewritten.
