# FINDING-322: FY/form filtering does not verify annual fact periods

- **Status:** Open — full-payload historical exposure confirmed; runtime period policy unmeasured
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Confirmed historical-period selection defect on two chosen frozen payloads; population/run incidence unmeasured
- **Affected:** _annual_facts, parse_company_facts and parse_company_facts_history
- **Related:** ADR-017/022/029; distinct from ADR-116/117's year-adjacency guards

## Confirmed code behavior

The shared selector filters fp == FY and form starting with 10-K, sorts by filed,
and keeps the last row per reported fy. It does not examine start/end duration,
frame, observation-period identity or same-filing ambiguity. Equal filed values
retain input order, making the last input row win a collision. The former
full-year docstring therefore described a guarantee the code does not implement.

At producing revision 0b759d02, a synthetic prior annual revenue is 100. The next
reported fy has annual revenue 120 and a short-period revenue 40, sharing the same
filed date, accession, form, fy and fp. Annual net income is 12. Ordering the short
row last selects revenue 40, growth -60%, margin 30% and a failed default screen.
Reversing those two rows selects 120, growth 20%, margin 10% and a passing screen.
Neither path refuses the mixed periods. A third accepted-shape case lets a
comparative-period row produce reported fy 2024 with period_end 2023-12-31.
Parent and independent data-engineering probes confirm these synthetic behaviors.
No source acquisition or search is needed for the witnesses.

These inputs demonstrate accepted-shape behavior, not that SEC CompanyFacts emits
the exact constructed rows. The initial synthetic review established no actual affected vendor row, production experiment,
false graduate or trading effect.

## Primary-source context and limits

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
says CompanyFacts aggregates company concepts across submissions and describes
annual, quarterly and instantaneous frame periods separately. The
[SEC Financial Statement Data Sets documentation](https://www.sec.gov/dera/data/fsds.pdf)
§3 describes filings containing multiple reporting periods; its submission fields
and numeric fact period-end/duration fields are separate. The
[EDGAR XBRL Guide, June 2026](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-06-29.pdf)
§3.1.8, printed page 32, defines fiscal period focus for the report.

Those sources support the distinction between reporting focus and fact periods.
They did not, in the initial review, establish the exact CompanyFacts JSON fy/fp mapping
or identify a real affected CompanyFacts row. Transferring the FSDS field meanings
to that JSON without further evidence would be an inference, not verified schema
identity. The risk to real production remains unmeasured.

## Disposition

Correct only the three parser docstrings and cold-memory claims. Preserve all
filtering, ordering, tie handling, fiscal labels, arithmetic, source calls and
screening behavior. This reporting correction does not close period selection.

A runtime correction requires an attributable frozen CompanyFacts fixture, a
separate ADR and TDD for duration concepts versus instantaneous balances,
non-December fiscal calendars, comparative periods, restatements and ambiguous
ties. Assigning fiscal years from end.year or applying one duration filter to
all concepts would introduce unsupported assumptions. Existing adjacency checks
operate after year assignment and do not establish observation-period identity.
No threshold, search, v14, generated record or frozen cohort changes.

## Verification

Final independent data-engineering and research reviews approved this reporting-only
correction in Codex session 5. Both separately checked the module against HEAD:
only the three intended docstrings differ. The data review independently rebuilt
all three synthetic witnesses. Foreground make check-all passed: 15,253 backend
tests (97.43% coverage), 746 frontend tests (97.88% statement coverage), lint,
formatting and types. No new behavior or TDD implementation claim is made.

Three complete synthetic claims and a prepatch module AST/docstring receipt are
preserved at /tmp/qf-w44-s3-period-probe.{py,json}; --compare checks unchanged
claims and the whole module AST except the three permitted docstrings without
writing receipts. Run from backend with PYTHONPATH=. and the offline UV cache.
The parent replay passed in session 5.
Official source text was verified through the web reader. Direct PDF download
returned HTTP 403; no rendered-table verification or CompanyFacts acquisition is
claimed.


## Session 5 addendum: actual CompanyConcept evidence

The free official [SEC Apple Revenues concept endpoint](https://data.sec.gov/api/xbrl/companyconcept/CIK0000320193/us-gaap/Revenues.json)
was available through the web reader on 2026-10-27 UTC. Its 11 USD observations
all carry fy 2018, fp FY, form 10-K, filed 2018-11-05 and accession
0000320193-18-000145, while their observation periods span different durations
and years. The final observation is 2018-07-01 through 2018-09-29, value
62,900,000,000, frame CY2018Q3. A 2017-10-01 through 2018-09-29 observation
with value 265,595,000,000 is also present.

At revision c917b706, passing that concept alone to the unchanged shared selector
selects the final 91-day observation for reported fy 2018. Reversing the input
rows selects the comparative 2015-09-27 through 2016-09-24 observation instead.
These are actual concept rows, strengthening the initial synthetic evidence
about reporting labels versus observation periods and the isolated selector's
order dependence. Parent and independent data/research checks agree. A parent
projection into a constructed CompanyFacts-shaped envelope produces the same
62.9-billion revenue in both parsers; that envelope was constructed for the probe.

This is a CompanyConcept response, not an acquired full CompanyFacts payload.
The primary API documentation describes CompanyFacts as the aggregation of all
company concepts; applying this isolated result to production is still an
inference until full-payload tag precedence and downstream use are checked.
No current production misstatement, affected experiment, screen verdict or false
graduate is established. Direct CompanyFacts access returned HTTP 403 and its web
reader URL was inaccessible; no retry or header bypass followed.

The frozen reader text and JSON reconstructed by joining its two numbered lines
are at /tmp/qf-w44-s5-sec-period/concept-web-reader.txt and
concept-normalized.json. They are reader artifacts, not raw HTTP response bytes.
Parent receipt parent-receipt.json records their hashes, executed revision,
module hash, selected rows and projected parser outputs. Independent data receipt is
/tmp/qf-w44-s5-sec-period-independent-data-engineer.json. All 11 rows
and order match between the reader text and reconstructed JSON. Runtime policy
remains open; neither a longest-duration choice nor fiscal end-year assignment
is justified by this isolated concept.

Addendum verification: independent data and research reviews approved the bounded
claims. Foreground make check-all passed again: 15,253 backend tests at 97.43%
coverage, 746 frontend tests at 97.88% statement coverage, and all lint, formatting
and type checks. Runtime source is unchanged by this addendum.


## Session 21 addendum: full CompanyFacts payload and downstream exposure

On 2026-10-30 UTC, one ordinary, keyless official SEC request using the unchanged
production User-Agent returned HTTP 200 and 3,789,099 raw bytes. The complete body
is durably frozen in [the attributed gzip fixture](../evidence/FINDING-322/README.md),
with raw SHA-256
`73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43`.
Unlike session5's reader artifact, this is the full acquired CompanyFacts response,
including all 503 us-gaap concepts and original array order. Retrieval metadata is
parent-recorded; both reviewers independently verified bytes, identity and parser
results without another request. No freshness or issuer-truth certification follows.

At revision `3018dfd0`, unchanged production tag precedence selects
RevenueFromContractWithCustomerExcludingAssessedTax before Revenues. The history
parser returns seven FY2019–2025 rows. FY2019 revenue is 64.040 billion USD for
2019-06-30 through 2019-09-28; FY2020 is 64.698 billion for 2020-06-28 through
2020-09-26: 91 days inclusive each. Selected net income and diluted EPS also use
those quarters (13.686/12.673 billion and 3.03/0.73). This establishes actual
full-payload historical parser exposure without projection or input reordering.

The same respective filed/accession/end groups include 364-day annual revenue
260.174/274.515 billion, net income 55.256/57.411 billion and EPS 11.89/3.28.
The annual rows lack frame; FY2019's selected quarter lacks it too. Neither frame
presence nor reported-fy adjacency supplies a valid general repair. Latest FY2025
snapshot revenue is annual (416.161 billion), with annual FY2024/2025 growth
0.0642551178283274. **This payload does not demonstrate a wrong latest snapshot.**

Parent and independent research also supplied explicit synthetic constant prices
of 10 to the actual parsed history and current valuation. Under those controlled
prices, substituting only the six literal same-filing annual scalars above changes
both own-history percentiles from 0 to 1/7 and the composite score from
0.9717424903153106 to 0.8765043950772154. Both results have seven observations
and no flags. All other valuation fields and the actual FCF-first DCF are exact
unchanged: growth 0.08998622735214545 and intrinsic value 117.96274231268941.
This is a constructed sensitivity intervention on real financial facts with
synthetic prices, not an actual-market score, production experiment, historical
backtest, split-adjustment claim, false admission, graduate or trading effect.
Do not infer corruption of the actual FCF-first growth path from this witness.

The former full-payload acquisition/tag-precedence/history-exposure evidence gap
is therefore resolved for this capture. Runtime policy, population/run incidence,
other concept periods, comparative/instant balances, fiscal transitions,
restatements, source authenticity and PIT remain open. Preserve the frozen bytes;
never refresh them or reconstruct historical generated results. This addendum
changes documentation/evidence only, with no parser, threshold, v14, generated
record or frozen cohort change. Independent data and research reviews approve the
bounded claims; full-gate and publication/CI receipts live in the session ledger.

## Session 22 addendum: second filer, June fiscal year and leap-year duration

One prospectively bounded ordinary keyless SEC CompanyFacts request on
2026-10-30 returned HTTP 200 and 4,936,836 complete bytes for MICROSOFT CORPORATION,
CIK 789019. Verified TLS, the unchanged production User-Agent, no automatic
redirects and no retry were used. Raw SHA-256:
`464cc12cc4796c90a6a0c709eb4920788aa7d4d5eee8b44f2d11d7d44804ae37`.
The [second immutable full-response fixture](../evidence/FINDING-322/README-MSFT-20261030.md)
retains all 562 us-gaap concepts and original array order. Transport metadata is
parent-recorded; independent reviewers verify local bytes and parser/source claims
without another request. The original Apple capture remains unchanged.

At producing revision 078bfd4a, the unchanged first-priority modern revenue tag
supplies nine FY2018–2026 history rows. Selected FY2018/2019/2020 revenue is
30.085/33.717/38.033 billion USD; net income 8.873/13.187/11.202 billion and diluted
EPS 1.14/1.71/1.46. All nine observations run April 1 through June 30 of the reported
year, 91 inclusive days. Literal same-fy/fp/form/filed/accession/end annual
alternatives exist in each respective concept array:

| FY | Accession / filed | Annual start / end | Days inclusive | Revenue USD | Net income USD | Diluted EPS |
|---|---|---|---:|---:|---:|---:|
|2018|0001564590-18-019062 /2018-08-03|2017-07-01 /2018-06-30|365|110360000000|16571000000|2.13|
|2019|0001564590-19-027952 /2019-08-01|2018-07-01 /2019-06-30|365|125843000000|39240000000|5.06|
|2020|0001564590-20-034944 /2020-07-30|2019-07-01 /2020-06-30|366|143015000000|44281000000|5.76|

Every annual alternative lacks frame; selected 2018/19 quarters also lack it,
while 2020 selected quarters have CY2020Q2. Frame presence is not a repair.
Latest FY2026 revenue 331.839 billion spans 2025-07-01 through 2026-06-30, 365 days;
FY2025 revenue 281.724 billion is also annual. Native latest growth is exactly
0.1778868679984666. Latest NI/EPS likewise span the annual period. This capture
establishes no wrong latest snapshot.

This strengthens source-grounded historical exposure across two chosen filers,
including June fiscal years and 365/366-day alternatives alongside Apple's
364-day alternatives. It does not estimate population/run incidence, calibrate
any duration rule or justify a universal selector. No prices, new scores,
financial-input substitutions, screen effects, historical experiments, PIT,
split correctness, issuer/source truth, graduates or trading effects are asserted.
Runtime duration/instant policy, comparative/restatement/transition handling and
ambiguous ties still require separate ADR/TDD. No parser, generated record,
threshold, v14, frozen cohort or historical output changes. Offline reproduction,
raw/compressed hashes and acquisition attribution accompany the fixture; final
review/full-gate/publication/CI receipts live in the session ledger.
