# ADR-420: Freeze one original filing context witness

- **Status:** Accepted — source-only protocol; acquisition still requires harness review
- **Date:** 2026-11-06
- **Deciders:** Codex W45 session5 under standing autonomy
- **Relates to:** ADR-017/022/029/399/419; FINDING-322

## Context and hypothesis

Independent research and data reviews approved this protocol before adoption.
Final harness conformance and pre-acquisition reviews are separate prerequisites.
The quality/value pivot needs truthful annual and availability inputs. The
CompanyFacts captures behind FINDING-322 lack authoritative DEI fiscal/report
anchors and acceptance timestamps. Retaining selected rows under ADR-419 does
not create these. A guessed duration band or end.year grouping would substitute
new assumptions for evidence. No original filing for the chosen accession is
already retained in the repository; its accession and both revenue witnesses
were published in FINDING-322 before this task.

Hypothesis: one original filing supplies its own fiscal/report anchor and XBRL
contexts that distinguish the known annual revenue from the known quarter.
This is a source-only known-defect witness, not an untouched market experiment.
It cannot improve the alpha case by itself. No annual selector, fiscal calendar,
restatement policy or historical availability estimator is adopted here.

## Source and immutable one-attempt policy

Fix CIK320193, accession0000320193-19-000119, and exactly this URL:

https://www.sec.gov/Archives/edgar/data/320193/000032019319000119/0000320193-19-000119.txt

This is the SEC's documented complete-submission symbolic path. Only generic
[access documentation](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data)
and [timestamp documentation](https://www.sec.gov/about/webmaster-frequently-asked-questions)
were consulted before adoption; target content has not been fetched or searched.
The SEC documents free public filing access, declared User-Agent requests and
complete-submission header timestamps. Acceptance is not first public observation;
post-acceptance corrections and the later capture date remain explicit limits.

Use the existing sweep USER_AGENT at published revisionc4322072, with
Accept:text/plain and Accept-Encoding:identity. One HTTPX GET, transport retries0,
follow_redirectsFalse, no credentials, environment proxies/auth disabled. No
browser reader, alternate endpoint, header change, filing index or fallback fetch.
Connect/read/write/pool timeouts10/15/15/10seconds; a60second elapsed ceiling is
checked between received chunks and can overrun by the current socket timeout.
Cap decoded retained body at64MiB; reaching the cap terminates acquisition rather
than increasing it. These are resource/error limits, not financial thresholds.
Record observed decoded chunk bytes separately from retained bytes when a chunk
reaches/exceeds the cap. Here raw body means retained HTTP-decoded response bytes,
not a claim to preserve wire framing or compressed transfer bytes.

Exclusive root `/tmp/qf-w45-s5-original-aapl2019` must be absent before the sole
invocation. Create it and durable START before HTTP; bind this protocol, executed
acquisition script, Git revision, HTTPX version and fixed source identity. Preserve
actual request/completion times, elapsed time, selected response headers, HTTP
status, final URL, exception/partial-byte state, raw byte count/SHA256 and mtime0
gzip. Empty/non200/redirect/timeout/oversize/interrupted starts are terminal
UNEVALUABLE or INCOMPLETE. No retry, resume, repair, re-root, alternate source or
second request for this registered accession. Offline retained-byte audits are
allowed; they never perform acquisition. Transport success is not scientific PASS.

## Fixed comparison, selection and acceptance

One deliberately chosen filing/known error, not a population sample. Zero price
requests, market trials, searched variants or portfolio observations. No effective
trial count is reset: existing technical/quality/value searches, ADR414–416,
terminal ADR417 and sealed ADR418 remain as recorded. Neither cohort is touched.
There is no new untouched return geometry, financed portfolio or trading-cost
estimate. Data access costs $0; all PBO/DSR/WF/holdout/graduation checks remain NOT
MEASURED. No broker, cloud dispatch, paid resource or generated-data writer.

Before financial interpretation, inventory EVERY SGML DOCUMENT type/filename and
hash, retain the SEC header and identify the10-K and anyEX-101.INS instances.
No assumption that the submission includes a standalone instance. A nonfinancial
page, missing identity, malformed structure or unavailable supported financial
representation must remain explicit, never a fabricated clean extraction.

An annual-anchor linkage PASS requires ALL of:

1. Header CIK/accession/type match the fixed source. Retain conformed report end,
   filed/change dates and acceptance timestamp exactly as supplied; do not assign
   UTC to an unlabeled header time or call it a contemporaneous vendor vintage.
2. The same filing's DEI DocumentPeriodEndDate, DocumentFiscalYearFocus,
   DocumentFiscalPeriodFocus and DocumentType resolve consistently to the header,
   year2019, FY and10-K. Retain their exact raw values and context references.
   Transition/amendment evidence, absent fields and disagreements stay explicit.
3. Original RevenueFromContractWithCustomerExcludingAssessedTax facts bind to
   BOTH fixed FINDING-322 witnesses: annual260174000000USD over2018-09-30 through
   2019-09-28 and quarter64040000000USD over2019-06-30 through2019-09-28. Require
   same-document context/unit resolution, issuer identifier320193, no dimensions
   or scenario for admitted witnesses, and no conflicting duplicate value.
   Retain all matching original fact/context/unit identifiers and attributes;
   do not pick a desired match from contradictory candidates.
4. DEI annual context and header report end support the actual annual interval;
   source classification is not inferred from the longest span, end.year, frame
   or reportedfy. Missing linkage is UNSUPPORTED, not a guessed annual repair.

Standalone XBRL is interpreted only as local XML without external entity/schema
requests. Inline XBRL is supported only when local XHTML parses, context/unit and
namespace references resolve, and exact numeric interpretation is supported:
plain decimal or standard dot-decimal grouping, integral scale in[-18,18], optional
minus sign, no continuedAt/fraction/nil. Exact Decimal arithmetic applies scale;
unknown transforms, continuations, ambiguous namespaces and numeric disagreements
are UNSUPPORTED. DEI date must be literal ISO or an unambiguous English month/day/
year value with its declared transformation retained; no locale or timezone guess.
This bounds the witness audit, not a general production iXBRL parser contract.

Record CAPTURED separately from linkage PASS/UNSUPPORTED/CONTRADICTED. Any absent
or conflicting requirement yields a qualified negative result. Do not loosen the
requirements, acquire another filing or reinterpret a quarter after inspection.
One source-only result cannot certify all filers, concepts, fiscal transitions,
PIT completeness, issuer truth or actual portfolio score correctness.

## Artifact packaging, verification and consequences

Retain complete raw response bytes at the exclusive root permanently. For the
repository, preserve the exact header, complete10-K and completeEX-101.INS
components plus full document inventory/source receipt. Each component is gzip
mtime0 with raw/compressed SHA and size. A component whose compressed size exceeds
450KiB is not split or truncated to bypass the existing large-file hook; record
it as not portable, keep root bytes and mark linkage evidence incomplete for
publication. Unrelated exhibits remain inventoried and root-retained, not copied
into a needless large repository artifact. Repository evidence is thus a declared
component extraction, not the entire unmodified submission.

Validate the acquisition harness offline before its single invocation (one call,
non200/redirect/size/exception preservation, exclusive start and no retry). Use
independent research/data pre-acquisition review and independent offline result
review, exact hashes and a deterministic no-network reproduction. No production
parser/scorer changes occur. Full foreground make check-all and exact publication
CI are required. No frozen source, cohort, timing root, threshold or data/*.json
changes. Acquisition failure is useful evidence of this source path's availability,
not evidence of negative returns or general SEC unavailability.

Alternatives: a shared annual duration filter is simpler but unsupported for
instant balances/comparatives/transitions; more attribution fields add size but
not anchors; buying PIT data violates the zero-cost boundary. The chosen single
source may still fail and does not solve broad history coverage. After this one
capture, pursue one integrated explicitly anchored period/availability policy if
supported; do not make an accession-by-accession evidence-mining chain.

Reversal: cancel before acquisition, retaining this decision. After START, keep
its terminal outcome and all evidence; removing an audit tool never authorizes
another attempt or repair of any frozen research.
