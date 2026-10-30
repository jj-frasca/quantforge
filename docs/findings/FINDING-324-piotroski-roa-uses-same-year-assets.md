# FINDING-324: Piotroski-inspired ROA trend uses same-year assets

- **Status:** Open — conditional frozen-source reversal confirmed; runtime source-alignment policy pending
- **Date:** 2026-10-27, Codex autonomous session5 (ISO2026-W44)
- **Severity:** Methodology mismatch confirmed on one frozen payload; population/run incidence unmeasured
- **Affected:** fundamentals/quality.py:piotroski_f_score and its quality/record consumers
- **Related:** ADR-029/117; distinct from FINDING-045 adjacency and FINDING-322 periods

## Primary definition and implemented claim

Piotroski's [original Journal of Accounting Research article](https://www.ivey.uwo.ca/media/3775523/value_investing_the_use_of_historical_financial_statement_information.pdf),
volume 38 supplement (2000), section 2.3.1, printed pages 7–8, defines ROA using
income before extraordinary items divided by beginning-of-year assets. The trend
signal compares the current and prior annual ROA. QuantForge instead divides
each year's net_income by that same row's total_assets, then compares the latest
two ratios. The source is therefore an inspired proxy, not an exact reproduction
of that ROA trend definition.

The original pages were downloaded with verified TLS and rendered for visual
inspection. PDF SHA256:
901d713553ddaf5b3cf60475d3a90aeaff5f584a6ceb2d0d33fd918ebed1b4e5.
Frozen source/receipt and inspected printed-page 7/8 renders are under
/tmp/qf-w44-s5-piotroski/. A local Python certificate-store failure was resolved
with system curl's verified TLS; certificate checks were never disabled.

## Exact synthetic witness

At producing revision 014c611e, take three consecutive reported years 2022–2024
with total assets 100, 1000 and 100. Prior/current net income is 10 and 15;
revenues are 100, 1000 and 100 to keep the implemented turnover ratios constant.
For this witness only, assume the income observations represent the intended
numerator and prior closing balances represent subsequent beginning balances.
Those assumptions isolate denominator timing; they do not certify vendor mapping.

The code compares current ROA 15/100 = 3/20 with prior 10/1000 = 1/100, awarding
the improving-ROA point. Beginning-assets scaling compares 15/1000 = 3/200 with
10/100 = 1/10, a decline. Exact Fraction oracles establish the reversal without
floating ambiguity. The implemented F-score is 2 (positive ROA plus improvement),
quality score is 2/9, and compute_fundamental_record retains those values. Changing
only this ROA trend point would give 1 and 1/9 in this deliberately isolated case;
that conditional substitution is not a complete paper-replication score.

A second case with assets 1000, 100 and 1000 shows the opposite direction: the
code misses the trend point that beginning-assets scaling awards. A constant-assets
control agrees. No actual vendor occurrence, affected experiment, false graduate,
trading effect or empirical return consequence is established.

Parent original receipt: /tmp/qf-w44-s5-roa-parent.json (quality source unchanged
from its 9338fe90 attribution through 014c611e). Independent data receipt:
/tmp/qf-w44-s5-roa-independent-data-engineer.json. The frozen three-case receipt
/tmp/qf-w44-s5-roa-baseline.{py,json} includes complete history, F-score, quality
and FundamentalRecord claims, exact ratios, source AST and docstrings. Its
read-only --compare mode checks unchanged claims and only the three permitted
documentation edits; run from backend with PYTHONPATH=. and the offline UV cache.

## Disposition and unresolved policy

Qualify the module, FScore and piotroski_f_score docstrings plus formal contracts
and the citation summary. Preserve every runtime formula, missingness branch,
score, flag and generated record. No new behavior or TDD implementation is claimed.

A correction needs a separate ADR/TDD covering three consecutive balance years,
missing/zero/nonpositive assets, period provenance and income-before-extraordinary
mapping. The current latest-two-row contract cannot reconstruct prior beginning
assets from those two rows alone. ADR-117's year-label adjacency does not prove
balance-period identity; F322 remains open. Positive-asset signs and comparisons
sharing a common denominator may be invariant, so the demonstrated trend-point
mismatch must not be generalized to every F-score component.

Other paper alignment is not certified by this witness. In particular, the paper's
turnover body text and Table 1 use different denominator descriptions; do not infer
a uniquely verified turnover recipe or silently change it. Diluted-share counts
also do not independently establish issuance history. No schema, parser, threshold,
search, v14, frozen cohort or historical-score repair is adopted here.

## Verification

Parent and both independent reviews reproduced all three complete claims and
exact Fraction oracles. The baseline replay permits exactly the module, FScore
and piotroski_f_score docstrings to differ. Each reviewer also compared directly
against HEAD and found no other module AST changes, checked the downloaded PDF
hash and visually inspected the two primary pages. Both approved all five paths.

Foreground make check-all passed: 15,297 backend tests (97.43% coverage),
746 frontend tests (97.88% statement coverage), lint, formatting and types.
Log: /tmp/qf-w44-s5-check324.log. Runtime scores remain unchanged and the
source-alignment policy remains open.

## Session 22 addendum: attributable FY2022 trend reversal

The immutable [full CompanyFacts capture](../evidence/FINDING-322/README.md)
from session21 supplies a literal-source witness for the denominator-timing
mismatch. Its raw SHA-256 is
`73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43`.
Unmodified parsing selects these observations, all FY/10-K USD facts:

| Concept / reported FY | Accession | Period start | Period end | Value USD |
|---|---|---|---|---:|
| Assets 2020 | 0000320193-20-000096 | instant | 2020-09-26 | 323888000000 |
| Assets 2021 | 0000320193-21-000105 | instant | 2021-09-25 | 351002000000 |
| Assets 2022 | 0000320193-22-000108 | instant | 2022-09-24 | 352755000000 |
| NetIncomeLoss 2021 | 0000320193-21-000105 | 2020-09-27 | 2021-09-25 | 94680000000 |
| NetIncomeLoss 2022 | 0000320193-22-000108 | 2021-09-26 | 2022-09-24 | 99803000000 |

The income observations each span 364 inclusive days. Selected closing balance
dates equal income ends; preceding selected balance dates are exactly one day
before the following income starts. Each following filing's same-filed/accession
comparative Assets observation exactly matches that preceding date and value.
Assets2020 is an actual closing instant, separately selected from F322's
quarter-duration FY2020 revenue/income. This is explicit period/value continuity
for this capture, stronger than reported-year adjacency alone.

Retaining parsed NetIncomeLoss conditionally as numerator, exact Fraction
comparisons reverse the FY2022 trend:

- Same-row closing assets: FY2021 `47340/175501` (0.26974205275183616),
  FY2022 `99803/352755` (0.2829244092925685), an increase.
- Previous closing as beginning assets: FY2021 `11835/40486`
  (0.29232327224225657), FY2022 `99803/351002` (0.2843374111828423), a decline.

A constructed prefix of the parsed history ending FY2022 yields F-score 8,
`delta_roa_positive=True` and quality 0.6675842309900554 in the unchanged scorer;
its no-price FundamentalRecord retains those numbers with value/combined absent.
Changing only this trend point would yield 7, a conditional isolated substitution,
not an executed repaired scorer or full paper-replication score. The prefix
retains the full history's **2025 accession envelope** `0000320193-25-000079`.
It is a present offline consumer probe, not a contemporary FY2022 artifact, PIT
backtest, historical production run or reconstructed contemporaneous filing.
The latest FY2025 trend increases with either scaling in this same capture.

Independent data and research reviews reproduce original rows, comparative matches,
exact ratios and consumer claims without network or financial-input substitutions.
The [offline reproduction command](../evidence/FINDING-324/README.md) preserves
these checks. Full-gate/publication/CI receipts live in the session ledger.
This closes the initial synthetic-only evidence limit for one conditional
source-grounded reversal. Equivalence of NetIncomeLoss to the paper's numerator,
source authenticity, PIT, population/run incidence, all other score components
and empirical/trading effects remain unestablished. Runtime source-alignment,
missing-balance and income policy still require a separate ADR/TDD. No scorer,
parser, threshold, generated record, frozen cohort or historical result changes.
