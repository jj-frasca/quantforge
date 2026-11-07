# ADR-422: Measure two-year quality-input coverage once

- **Status:** Accepted — source requests require final frozen-harness review
- **Date:** 2026-11-07
- **Deciders:** Codex W45 session7 under standing autonomy
- **Extends:** ADR017/022/029/116/117/420/421; FINDING322

Independent research and data reviews approved this protocol before adoption.
Both requested clarifications are incorporated below. No target requests, code
or cohort root creation preceded adoption.

Purpose: one integrated bounded coverage result, not another per-accession witness
or helper-only publication. Determine whether free current source captures can
populate two explicit adjacent annual histories for existing quality scoring under
ADR-421's exact annual-flow/instant/observed-availability policy. No value/combined
score without a price; no historical PIT or alpha claim. Existing F324 scorer
qualifications remain. Related ADR-417/418 and every old cohort/root stay frozen.

Fixed purposive roster in this order: IBM CIK51143, KO21344, NFLX1065280,
COST909832, WMT104169. IDs only inspected, no scores/ranks/returns. Pin published
84eab898c3f0c0dd07a4c8915c60fb12176e2c87 and canonical hashes of these original
fundamentals-pool rows before code/requests. Five selected businesses are not a
population sample or an investable universe. No issuer substitution after failure.

One exclusive root /tmp/qf-w45-s7-two-year-quality-coverage, absent until sole live
invocation. Live start must be before 2026-11-07T11:00:00Z; otherwise NOTRUN/EXPIRED,
no renewed window/root. No live requests before all offline TDD and independent
research/data harness reviews approve exact code. Freeze protocol/code/tests/
dependencies/roster hashes in durable START before HTTP. One invocation only;
interruption INCOMPLETE permanently, no resume/retry/reroot or replacement study.

At most20 GETs serially, no key/auth/environment credentials/proxies, no redirects,
transport retries0, existing fundamental-sweep User-Agent verbatim, Accept-Encoding
identity. Use existing locked httpx/lxml only, capture versions/module hashes and
app421 hash. At least0.2s between starts. Per request connect/read/write/pool
10/15/15/10s;60s elapsed check during chunks. Each retained decoded body capped64MiB;
whole cohort retained raw capped256MiB. Total raw+gzip disk bounded approximately
512MiB; observed bytes may exceed retained cap by one received chunk. Overall600s
elapsed ceiling checked before/after stages and during receive. It may overrun by
the current socket timeout or current bounded parse/write operation; never renew.
Keep actual request/completion UTC times, status/finalURL, selected headers,
exceptions/partial bytes, observed vs retained bytes, body SHA and mtime0 gzip.
All bodies are HTTP-decoded retained bytes, not wire framing.

Per issuer: one GET https://data.sec.gov/submissions/CIK{10digits}.json. Validate
CIK, same-length recent accessionNumber/form/filingDate/reportDate arrays, original
scalar string types/accession paths and no duplicate accessions. Require valid
filing/report dates on ALL exact-form10-K candidates before selecting; an invalid
10-K refuses selection rather than being skipped. Noneligible forms may have empty
reportDate; never reject an issuer merely for that unrelated empty label. Select two latest
distinct exact-form10-K rows sorted descending filingDate then accession. No10-K/A,
10-KT, earlier-files pages, alternate endpoint or extra lookup. Fewer than two is
terminal source-selection failure. Seal BOTH original rows/accessions durably
before either complete-submission request. Request older chosen filing then newer
at https://www.sec.gov/Archives/edgar/data/{intcik}/{accessionNoDashes}/{accession}.txt,
then one CompanyFacts GET https://data.sec.gov/api/xbrl/companyfacts/CIK{10digits}.json.
At most4 GETs per issuer. First transport/identity/anchor/selection failure ends
that issuer; remaining predeclared issuers still run within fixed caps. No alternate
filing, hidden retry, source fill, source reuse from old roots or data repair.

Before exposure freeze the supported original-anchor domain: one unique primary
10-K DOCUMENT in complete SGML, complete header/inventory/primary hashes retained;
local well-formed inline XHTML only. No standalone fallback, HTML recovery, remote
schema/entity references, DTD/entity processing, guessed date/fiscal-year mapping.
No network in extraction. Use secure lxml parser with entity resolution/network/
DTD loading disabled, reject entity declarations/DOCTYPE under this bounded domain.
Namespaces resolved locally; primary header issuer/accession/form/report-end must
bind selected submissions row and DEI. Duplicate/missing context IDs refuse.
Admitted contexts require unique SEC CIK identifier, no segment/scenario/dimensions,
ISO date-only duration with start<end. Every required DEI fact must resolve to the
same issuer and exact annual interval ending at report end. Require consistent
DocumentType10-K, DocumentFiscalPeriodFocusFY, four-digit DocumentFiscalYearFocus,
DocumentPeriodEndDate, DocumentAnnualReport=true and DocumentTransitionReport=false.
Absent or instant-only annual/transition evidence is UNSUPPORTED, never defaultFalse.
All eligible duplicate DEI values/periods must agree; unknown representations,
transforms, nil, continuation or namespace ambiguity are UNSUPPORTED.

Supported DEI lexical forms: plain literal type/FY/year, ISO dates without an
unknown transform, and explicit known XBRL English month-name date transforms
2011/2015/2020/2022 (freeze exact URI/local-name set in reviewed method). Do not use
ambient locale, numeric ambiguous dates or longest duration. Annual/transition
flags support literal XML boolean true/false/1/0 without format, or SEC boolballotbox
in exact http/https2015-08-31 namespace (U+2610false, U+2611/U+2612true). Other boolean
transforms unsupported. Retain all original DEI nodes/context/namespace attributes
and original raw header labels, not just normalized anchor. Prior420 is a positive
offline control, not a general parser imported with changed hardcoded globals.

Evaluate both years using unmodified app421 over the SAME new CompanyFacts bytes
and each supported explicit filing anchor. Exact policy covers all14 raw source
concepts (flows incl weighted shares; report-end instants with absent start).
Conflicts refuse, absent optionals stayNone, required revenue refuses. Require
consecutive fiscal labels AND prior_report_end+1day==next_annual_start, distinct
accessions/same issuer. Never create an earlier label from a comparative context.
Assemble one two-year history, newest anchor citation, existing no-price record,
and retain BOTH original year wrappers/source graphs/availability beside it.
Eligibility=max(all actually observed source completions), never filed labels.

Comparison fixed: legacy CompanyFacts fields for the exact two fiscal labels
versus both anchored results; record absent legacy years as absent. No new prices,
rank selection, market/configuration trial, financed account, return geometry,
cost/exposure/turnover/drawdown or benchmark. Source/resources$0; all PBO/DSR/WF/
holdout/graduation checks NOT MEASURED. Prior technical/quality/value trials,
ADR414–416/417/418 are disclosed, not reset or pooled. No current-value inference.

Acceptance: all5 planned issuer attempts durably reach terminal outcome; strict
coveragePASS only if all5 have two supported consecutive physically contiguous
annual anchors, all13 populated annual-model financial scalar outputs attributable
for both years (derivedGP/FCF allowed only aligned operands), and existing quality
scorer consumes each complete two-year evidence wrapper. Price/value/combined
remain unknown. A completed study reports counts/statuses, no population coverage
probability/p-value. Any failing issuer makes overallcoverageFAIL and stays in the
denominator. Failure before all planned attempts yields INCOMPLETE, no partial
success fraction. Preserve distinction transport/unsupported/missing/conflict/
continuity failures; source failure is not a negative-return observation. Never
patch the method after source exposure, retry a failing issuer or acquire a sixth.

Packaging fixed: retain every full raw/gzip source at root permanently. Publish
complete JSON or complete primary10-K/header components individually only if each
mtime0 gzip<=450KiB; otherwise explicitly root-only, never split/truncate/omit
unfavorable fields to evade hook. Full inventory/transport/selection/start/terminal
receipts and exact executed methods/tests/reviews/versions always portable.
Portable completeness is a separate verdict from coverage, no claimed full public
reproduction when any required body is root-only. If metadata/method package itself
exceeds cap, publication acceptance fails explicitly, never split solely to evade.

TDD/offline review before sole invocation: original420 and synthetic positive/
non-December controls; context/DEI/transform/checkbox conflicts and unsupported
branches; physical continuity, availability and evidence retention; submissions
array/tie/identity/duplicate selection; seal-before-request; non200/redirect/timeout/
partial/caps/exclusive-start/expiry, failing-issuer-then-next and no retry. Properties
for order invariance and physical geometry. Required reviews freeze code FIRST;
actual source reviews only replay exact retained bytes, never reinterpret/change
criteria to make coverage pass. Foreground fullgate, one explicit commit/freshsync/
push/exactCI after actual result. Do not publish helper-only fragments.

Primary references consulted before target content: SEC API docs and EDGAR access
path docs, XBRL2.1 context/period/entity spec, XBRL transformation registries and SEC
October2026 XBRL Guide checkbox table. Generic docs only; no five-issuer filings,
CompanyFacts or submissions content inspected yet. Next economic outcome remains
ADR418's already registered February11 final screen, with no interim economics or
new equivalent return cohort. A later full gate still needs qualified inputs,
price/split/value policy and sufficient untouched return geometry.

If independent result review discovers an implementation/method defect, record
UNEVALUABLE/INVALID_METHOD separately from supported-domain coverage failures.
Preserve the sole attempt and all source bytes, never repair/replay the cohort
under changed code. Even a completed all-five failure describes this declared
method/source domain, not general SEC input availability.

Clarifications fixed before adoption:
- Thirteen required financial model outputs differ from fourteen raw concepts.
  Missing COGS is acceptable when direct GP supplies gross_profit; all derivation
  operands still must align. The approximate disk bound includes gzip overhead
  and metadata and is not an asserted strict filesystem quota.
- Accession prefix identifies the submitting entity, which may be a filing agent.
  Do NOT require prefix==issuer CIK. Bind exact accession independently, issuer
  CIK in the path/submissions/header/context, and report dates separately.
- Supported date-format pairs are the 2011-07-31/2015-02-26 XBRL transformation
  namespaces with datemonthdayyearen or datedaymonthyearen, and 2020-02-12/2022-02-16
  namespaces with date-monthname-day-year-en or date-day-monthname-year-en, all
  under http://www.xbrl.org/inlineXBRL/transformation/. Unknown pairs refuse.

Primary references:
https://www.sec.gov/search-filings/edgar-application-programming-interfaces
https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
https://www.xbrl.org/Specification/XBRL-2.1/REC-2003-12-31/XBRL-2.1-REC-2003-12-31%2Bcorrected-errata-2013-02-20.html#_4.7
https://www.xbrl.org/Specification/inlineXBRL-transformationRegistry/REC-2022-02-16/inlineXBRL-transformationRegistry-REC-2022-02-16.html
https://www.sec.gov/files/edgar/xbrl-guide.pdf (October2026, checkbox table page189)

Reversal: cancel before START with an explicit retained CANCELLED receipt. After
START, preserve all terminal evidence; removing the harness never authorizes
reacquisition, changed-method replay or replacement of this or another cohort.
