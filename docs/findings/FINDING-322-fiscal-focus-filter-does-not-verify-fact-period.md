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

## W45 session3: selected-flow input evidence contract (ADR-419)

The historical portfolio attempt ADR-417 is terminal UNEVALUABLE; ADR-418 has
sealed future inputs before entry. Neither permits repairing/replacing old
cohorts or treating current-score historical broadcasts as untouched evidence.
The next bounded capability retains selected revenue/NI/EPS source rows through
new fundamental records. This will expose actual observation periods and filed
labels needed for a coherent annual/instant/availability policy. It does not
change the selector, scalars, scores or validation thresholds and cannot certify
PIT or repair the documented quarters. ADR-419 fixes the comparison and exact
acceptance before implementation; no new market experiment is authorized.

Recovery verification (W45 session5): the inherited pre-code test log records
11 collected failures; the completed implementation passes all 11 tests, including
same-filed row-order binding, JSON round-trip, legacy omission, detached immutable
metadata, unchecked nested-copy refusal and whole-winner merge. Independent
baseline replay on both frozen full-source captures preserves complete history
and snapshot outputs outside the optional additions, plus record scores/flags at
prices absent, 10, 100 and 1,000. All 4,260 legacy records retain their canonical
payloads; source fixtures, ADR-417 receipts and ADR-418 cohort bytes stay exact.

The actual added pretty-JSON record footprint is 8,900 bytes for the chosen Apple
history (7 years/21 flow facts) and 11,350 bytes for Microsoft (9 years/27 facts).
Mechanical extrapolation to 4,260 filers gives 37.914–48.351 MB **additional**
bytes, not a population estimate or a bound on total pool size. Storage expansion
must be monitored as new cloud-written evidence accumulates; no generated file is
rewritten here. The alpha case is unchanged. The next useful input experiment is
one coherent annual-flow/instant-balance/availability policy, checked against
frozen source rows before any separately adopted portfolio evaluation. Do not
extend this work as a chain of per-concept metadata additions.

Review chronology is explicit: the preserved independent data review approved the
contract before implementation; the fresh independent data and research reviews
approve recovery after implementation. No missing pre-code research approval is
inferred from the interrupted ledger. This production-only lineage change adopts
no new experimental policy and produces no new return evidence.

## W45 session5: missing annual anchors, before source acquisition

The current research scorecard remains 0/41 universe-deflated survivors over
6,627,085 recorded lifetime trials. Existing quality/value long/short experiments
use conditional static scores; the funded historical ADR-417 attempt is terminal
UNEVALUABLE, and ADR-418's future cohort is sealed. None is rerun here.

Independent source triage establishes a narrower input blocker: the two frozen
CompanyFacts payloads contain no DEI DocumentPeriodEndDate, DocumentFiscalYearFocus
or DocumentFiscalPeriodFocus and no acceptance timestamp. Their fiscal labels
alone cannot authenticate an annual reporting anchor or historical availability.
ADR-419 retains selected-row evidence but does not supply those missing anchors.

Before acquiring another source, ADR-420 will fix one original filing capture:
Apple accession 0000320193-19-000119, already identified in this finding's frozen
same-filing comparison. Hypothesis: that filing's own fiscal/report metadata and
XBRL contexts can bind the known 2019 annual revenue 260,174,000,000 and quarter
64,040,000,000 to distinct actual intervals. This is one deliberately chosen
known-defect witness, not a random sample or a market experiment. Zero new price
requests, searches, parameter variants, portfolio returns or gate measurements.
Independent review must approve the final protocol before the sole acquisition.
The source attempt can fail or be unsupported; neither permits another request,
an alternate URL/header, an inferred annual band or a repaired frozen cohort.

Acquisition harness chronology: initial pytest collection failed on a protected
unrelated `/tmp` directory. A draft was already written before that error was
noticed, so the later missing-target control run is **not** called pre-code RED.
The draft is preserved separately. Subsequent genuine behavioral failures caught
late-chunk data loss and absence of an immediate HTTP-request timestamp; narrow
fixes followed those failures, and all 17 offline acquisition checks pass.
The parent independently reran those 17 checks. These are source-protocol controls,
not a new strategy experiment or financial threshold adjustment.

### ADR-420 terminal source result: filing-local linkage PASS

The sole request returned HTTP 200 on 2026-11-06 at 23:31:18–19 UTC, retaining
12,861,616 decoded bytes (SHA256
`c77a7ab405b61398dcbd7b0ecb98191b24c9519d9b18689c280c2ac7e4ebf4ab`).
The attempt root is permanently frozen; no retry or further request is permitted.
The unmodified, pre-acquisition audit passes the fixed linkage criteria. Both
independent reviewers reproduce the full result and the complete financial graph
using the portable repository components alone, with distinct exact-arithmetic
and source-context checks. No acceptance rule changed after exposure.

The 96-document submission supplies an inline primary 10-K, 301 contexts, 9 units,
62 revenue candidates and the 4 required DEI facts. All four DEI facts bind
`FD2019Q4YTD`: FY2019, FY, 10-K and report end 2019-09-28, over the explicit
2018-09-30 through 2019-09-28 annual context. Three agreeing annual revenue
presentations scale `260,174` by 10^6 to exactly USD 260,174,000,000. One quarter
presentation in `FD2019Q4QTD`, 2019-06-30 through 2019-09-28, scales `64,040` by
10^6 to USD 64,040,000,000. The admitted contexts have issuer 320193 and no
scenario/dimensions; unit `usd` resolves to ISO4217 USD. No conflicting admitted
value appears. This supplies a direct filing-local annual anchor for this known
error without inventing a permissible duration band or an end.year fiscal rule.

Raw header acceptance is `20191030181236`, filed-as-of date `20191031`, and
change date `20191030`. They are retained as different source labels, with no
UTC or earliest-public-availability inference. A 2026 archive capture remains
subject to post-acceptance corrections and does not certify a 2019 data vintage.
No score correction, fiscal-transition handling or PIT portfolio follows.

The [evidence and no-network reproduction](../../docs/evidence/FINDING-322/AAPL-2019-original-filing/README.md)
preserve exact header/footer and the complete primary 10-K block (179,177-byte
gzip), all 96 inventory hashes, transport/start receipts, pre-acquisition method
identity and actual audit. The full raw response and unrelated exhibits remain
at the frozen root; repository components are explicitly not advertised as the
entire submission. No component exceeds the fixed 450 KiB compressed limit.
The reproduction normalizes in-memory tuples to their persisted JSON list shape;
its first unnormalized comparison failed on that envelope mismatch, not a fact
or criterion. Final reproduction passes without code or source changes.

**Alpha verdict:** unchanged; zero new market prices, return comparisons, search
trials or gate measurements. One demonstrated input blocker is partly resolved:
this filing can supply its own annual anchor and distinguish the known quarter.
The next concrete input experiment is one integrated opt-in selection policy that
uses explicit filing anchors for flows, end-matched instant balances and declared
conservative availability labels. It must preserve unsupported/ambiguous cases
and compare source-bound outputs before any separately adopted economic test.
Do not mine another accession or refresh either frozen portfolio cohort. ADR-417,
ADR-418, the older CompanyFacts captures and all generated records stay unchanged.

## W45 session7: integrated anchored input policy, before implementation

The demonstrated obstacle to the quality/value portfolio is truthful period and
availability evidence, rather than a missing ranker. ADR419 preserves selected
rows; ADR420 supplies one independently audited original annual anchor. Neither
makes the current CompanyFacts selector annual or its later capture historical PIT.
After checking completed receipts, independent research and data reviews approve
ADR421's ONE opt-in annual-flow/instant-balance/observed-availability policy.

Before tests or actual new selection, fix the comparison: use only frozen AAPL
CompanyFacts raw SHA73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43
and ADR420 FY2019 anchor/accession0000320193-19-000119, annual2018-09-30 through
2019-09-28. Compare one policy result to the unchanged legacy FY2019 row; never
construct another fiscal-year anchor or fetch a source to improve coverage.
Revenue must match the previously known annual260174000000 rather than legacy
quarter64040000000. Every other field must meet the same predeclared period/unit/
accession policy or stay missing/refuse on contradiction. Other fields remain
later CompanyFacts claims; ADR420 independently audited revenue only.

Zero prices, searches, parameter/economic trials, cost accounts or new return
geometry. No untouched return test exists in this known-witness comparison. All
PBO/DSR/WF/holdout/graduation checks remain NOT MEASURED. Capture/resource cost$0.
All prior selection remains disclosed, including ADR414–416, terminal417 and sealed
418. No effective-N reset, old-root modification, generated write or new cohort.
Acceptance is attributable aligned inputs plus honest observed-source cutoff,
source/row-order invariance, explicit missingness/conflict refusal and existing
scorer integration retaining its evidence wrapper. Value/combined remain unknown
without a price; the unchanged one-year F-score zero is insufficient history,
not measured poor economics. Independent implementation/result review and full
foreground gates are required. Alpha case is unchanged until economic evidence.

### ADR421 offline known-witness result

The opt-in evaluator admits14 same-accession source fields, no missing optionals,
for the single explicit2018-09-30..2019-09-28 annual interval and matching report-end
instants. Revenue260.174bn/NI55.256bn/EPS11.89/GP98.392bn replace the legacy
quarter64.040bn/13.686bn/3.03/24.313bn. Other scalar fields match. No default
selector or historical/generated record is changed. Actual-source observation
eligibility is2026-11-06T23:31:19.474972Z;2019as-of requests refuse.

The retained wrapper reaches the existing no-price FundamentalRecord producer.
Value/combined stayNone; F-score0 is its insufficient one-year history behavior,
not a poor-business finding. Only original revenue has ADR-420's independent XBRL
linkage audit; other fields are later aggregate claims matching the supplied
anchor, not certified original/split/PIT facts. Full inputs/rows/comparison and
read-only reproduction live in docs/evidence/ADR-421/. Alpha case NOT improved;
one input capability improved. Full truthful history/coverage and untouched
portfolio economics remain unmeasured. No cohort, threshold, price or trial reset.

## W45 session7: finite two-year quality coverage, before implementation

After ADR421's exact publication CI passed and the mission was reread, independent
research/data review approved ONE prospective-observation input-coverage study
under ADR422. Five fixed purposive issuers (IBM/KO/NFLX/COST/WMT), two original
annual filings each, no prices/returns/ranks/economic trials. This advances the
one-year capability to test whether two physically contiguous annual inputs can
reach the existing quality scorer. It is not a full value pipeline, a historical
PIT panel or alpha. All prior cohorts and trial accounting stay frozen.

Hypothesis, source policy, comparison, complete-denominator accounting and strict
acceptance are fixed in ADR422 BEFORE tests/code/new target content. Required
inputs may be unsupported or missing; that is useful method-domain coverage
information, not negative economics. Implementation defects instead make the
study UNEVALUABLE/INVALID_METHOD. Neither outcome authorizes altered-method
replay, replacement issuers or more source requests. No helper-only publication
or repeated accession-witness chain. New actual source root remains absent.

Pre-adoption reviews clarified that unrelated submission forms may have empty
report dates, malformed eligible 10-Ks must refuse rather than be skipped, and
13 required financial outputs differ from 14 raw concepts. SEC access documentation
also explicitly allows a filing agent's CIK in the accession prefix; issuer identity
must bind via the URL/submissions/header/context, never prefix equality. These
are design constraints fixed before source exposure, not observed incidence claims.

Before ADR422 target acquisition, research review additionally confirms a generic
interpretation limit: EPS and weighted-average shares from distinct original
annual accessions may use different stock-split bases. Exact period attribution
and a complete two-year wrapper do not establish corporate-action comparability.
The existing no_dilution component and resulting quality score remain conditional;
this study measures neither comparable split bases nor investable quality. No
issuer-specific split facts were inspected for this qualification. No source,
scorer, acceptance criterion or trial geometry changes; do not adjust target
values after exposure to make a score look comparable.

Offline harness review before source exposure found coordinator/parser defects
that would have distorted this coverage measurement: the twentieth successful
request could be treated as incomplete; English dates depended on ambient locale;
malformed context structure could pass; and unrelated binary exhibits could reject
a supported primary. Targeted RED controls preceded corrections. Further controls
separate legacy diagnostic refusal from anchored coverage, reject spoofed DEI URI
suffixes, preserve review receipts before HTTP, and classify unexpected method/disk
errors distinctly. These are pre-acquisition synthetic/retained-control findings,
not observed five-issuer incidence. All are consolidated within this one study;
no new source look or acceptance threshold change was used to obtain a fix.

## W45 session9: ADR422 permanently NOTRUN/EXPIRED

Recovery of the four owned dirty paths found the fixed November7,2026 11:00UTC
start deadline already passed (actual clock18:01UTC), registered root absent,
and no final PREACQUISITION manifest. The inherited work stopped during offline
harness preparation. Under the unchanged protocol this is terminal NOTRUN/EXPIRED;
no live invocation, renewed window, retry, reroot or replacement is permitted.
All667 protected source/cohort/generated-file baseline hashes remain exact.

The original protocol, roster, unfinished method/tests and actual offline TDD
receipts are retained in docs/evidence/ADR-422/. Synthetic67PASS does not supply
five-issuer coverage evidence or final frozen-harness approval. No production
capability is adopted in this closure. Zero recorded issuer attempts is not a
coverage fraction; the source/history/quality hypotheses remain unmeasured,
not rejected. Alpha case NOT improved; all financial gates and economics NOT
MEASURED, existing trial accounting unchanged. ADR417 remains terminal and
ADR418's sealed future final evaluation remains the next economic observation.
Do not manufacture another equivalent cohort to recover the expired attempt.
