# FINDING-351: Quality/value portfolio needs post-publication account evidence

- **Status:** Open — terminal UNEVALUABLE; complete-source/PIT blocker remains
- **Date:** 2026-11-06, Codex W45 session 3
- **Governing protocol:** ADR-417

Existing cross-sectional quality/value experiments broadcast supplied static scores
across earlier price dates and construct dollar-neutral legs. They measure a
conditional snapshot strategy; their selected statistics do not establish the
requested funded long-only top-quintile portfolio's post-publication performance.
ADR-416 is complete and remains frozen. Its measured MinTRL failure supplies no
permission to repeat history-length searches.

The concrete evaluation obstacle is an unavailable historical PIT score series
plus absence of a funded fixed-unit long-only account in that path. A published
August score archive permits one narrow subsequent-period exploratory comparison
without backfilling today's scores. It does not reconstruct historical filing
truth or turn a policy chosen today into a preregistered August policy.

ADR-417 fixes hypothesis, historical input blobs, ranking, period, costs, controls,
selection accounting, one-attempt source policy and economic screen before ranks
or new prices. Gate status remains NOT MEASURED. No alpha case has improved yet.

## Pre-acquisition implementation verification

Independent research and data reviews both caught a final-sale path error in the
new evaluator before any actual outcomes: replacing the terminal marked value
with cash omitted an exit-fee drawdown when the last close made a new high.
The [1,2] price / 10bp cost oracle failed first, then passed after preserving
all pre-sale marks and appending liquidation cash. Failed quality reports now
also persist in full, after an observed missing-receipt regression failure.
These are corrections to this new account, not changes to deployed gates.

Actual TDD receipts: 15 missing-module failures for selection/account before
implementation; 5 missing-source-boundary failures with 15 controls green;
1 missing-driver failure; 1 liquidation-path failure; 1 failed-report failure.
Final 23 focused synthetic tests, ruff and strict mypy pass. The first attempted
shell file creation used an incorrect cwd-relative path and collected no tests;
that attempt is excluded from RED evidence. No actual ranks or prices were
inspected during either independent review.

## Registered result: UNEVALUABLE (2026-11-06T13:09 UTC)

The fixed archive contains 3,224 records (1,574 with combined scores globally).
The archived S&P roster admits **283** combined-scored names; the fixed
ceil-top-quintile selection is **57** names. Current cross-sectional pool context
is **35** retained experiments and represented lifetime maximum **4,077**;
unpersisted ADR-416 attempts remain additional selection uncertainty, not zero.

Exactly one registered invocation reserved `/tmp/qf-w45-s3-adr417` before any
source call. It attempted **23 of 284** required series (283 names + SPY) in
roster order. First 22 canonical series passed the quality/calendar boundaries;
**AVB returned zero bars**. Its unchanged quality report fails `insufficient_data`.
All 23 attempts, 23 canonical sources (including the empty list), 23 full quality
reports and 22 successful evidence envelopes are preserved. There are 46 total
quality issues across these reports, including the terminal error. The vendor's
"possibly delisted" text is not a diagnosis of the actual cause.

The terminal receipt is **UNEVALUABLE**. The remaining 261 series were never
requested. No account return, drawdown, benchmark excess, screen verdict or
partial-subset performance was calculated. No retry, replacement, reroot or
resume is permitted. This is an input-availability failure, not evidence against
or for the economic hypothesis. All financial gates remain **NOT MEASURED**.
The shell exits normally after writing the explicit UNEVALUABLE receipt; exit0
means the driver recorded its terminal state, never that the economic screen passed.

The alpha case **did not improve**. Capability improved: a verified funded account
and historical-publication selection now exist. The biggest demonstrated obstacle
is complete, causally available input evidence, rather than an isolated numerical
guard or an additional technical signal. The historical vendor snapshot is not a
truth guarantee and the 56-session geometry cannot satisfy the existing gate.

## Next concrete experiment

Independently pre-register a genuinely prospective combined-score top-quintile
portfolio using one published current score/roster snapshot, identical funded
cost account and EW/SPY/cash controls, fixed future entry/exit dates and one final
look. Seal the exact selection and availability evidence before the entry close.
First assess input availability without selecting a more convenient historical
winner; this must be a new future protocol, never replacement of ADR-417's failed
historical cohort. A short prospective economic screen remains a lead, not a
PBO/DSR/WF graduate. Credible full-gate evaluation additionally needs sufficient
truthful historical score vintages; no shorter horizon or dummy grid may waive it.

## Independent final receipt audit

Research independently reproduced eligible283/top57 ordering from the pinned
historical blobs, all source hashes, issue/report counts, archived publication
context and terminal absence of accounts/screen fields. Data independently
reviewed the same source/calendar contract. No source reacquisition or partial
performance calculation was used. Exact executed module, driver and protocol bytes are separately preserved in
`executed-code.tar.gz` and match acquisition hashes. Subsequent test-only
annotations/ruff leave the acquisition-time test hash historical. The first
full gate then found an existing repository policy failure: drivers cannot own
literal history dates. Original focused test failed before correction; library
STUDY_START/END now supply the same dates to both driver and quality boundary.
No acquisition was repeated or scientific policy changed. New23 plus existing7
history tests pass. The original full run was 17,812 passed/1 failed; it is not
reported as green. A fresh full gate is required before publication.

Fresh foreground `make check-all` passed: 17,813 backend tests (97.50%
coverage), 781 frontend tests (97.89% statements), lint/format and strict types.
Both independent final reviews approved the frozen evidence. Validation success
means the implementation passes its tests; it does not change UNEVALUABLE into
an economic pass.

## Separately registered next experiment (ADR-418)

After the historical unit's green publication, ADR-418 seals a new published
current-score cohort before future entry:412 eligible/83 selected, Nov9 close–
Feb10 close,64 scheduled closes/63 return intervals,10bp each side and matched
EW/SPY/cash controls. Its future outcomes remain untouched at registration;
no study prices are acquired now. Exact pre-open publication and a fixed final
execution window are required, with no date sliding or cohort replacement.
Source completion remains unresolved (413 required series), and even a future
strict economic-screen success would be a lead, never full-gate alpha. ADR-417
remains terminal UNEVALUABLE with no retry or source reuse. Evidence capability
improved; the alpha case has no new economic observation yet.
