# FINDING-353: SEC's flattened historical statements are not an exact PIT panel

- **Status:** Source-documentation feasibility assessment complete; no dataset adopted
- **Date:** 2026-11-13, Codex W46 session22
- **Scope:** Candidate historical source for the quality/value portfolio, not a production defect
- **Related:** ADR-029/095/418/421/423/424; FINDING-322/352

## Question and comparison

Finding352 establishes that the current Git score archive cannot supply the
unchanged 252-search +252-holdout geometry. It does not establish that historical
fundamentals cannot be reconstructed elsewhere. Assess one distinct candidate:
can SEC Financial Statement Data Sets (FSDS) alone supply the exact annual-flow,
balance-date and availability evidence needed for historical combined-score
portfolios, compared with ADR421/423's attributed source contracts?

Independent research and data-engineering reviews were requested before any
dataset acquisition. This is retrospective documentation review, not a blind
experiment or a source-coverage measurement. F322 already cited the legacy FSDS
PDF for fiscal-focus semantics; this review follows the current landing page's
documentation link and checks the additional loss of period precision. No ZIP,
issuer filing, price, score rank or study outcome was acquired.

## Verified primary-source facts

The [SEC landing page](https://www.sec.gov/data-research/sec-markets-data/financial-statement-data-sets)
lists historical downloads from 2009 through 2026Q3. It reports December2024
reprocessing of historical sets to use primary-statement rendering, with a new
segments field. Historical coverage therefore exists outside the Git archive;
current extraction is not evidence of identical historical downloadable bytes.

The linked [current ten-page specification](https://www.sec.gov/files/financial-statement-data-sets.pdf)
differs from F322's [legacy nine-page PDF](https://www.sec.gov/dera/data/fsds.pdf).
Current §5.1, PDF page6, rounds SUB.fye and SUB.period to month ends. It records
acceptance as a datetime string without a zone in its format; prevrpt describes
subsequent amendment. §5.3, PDF pages8–9, rounds NUM.ddate to month end and qtrs
to whole quarters, with zero denoting an instant. Values have at most four
fractional decimal digits. The NUM key includes segments and coreg. It has no
exact start-date column. These are specification claims, not inspected rows or
measured incidence.

## Consequence for the proposed route

Rounded dates and durations cannot by themselves prove the physical annual
intervals and matching balance instants required by ADR421/423. Matching rounded
period labels is insufficient; assuming month ends would reintroduce the source
identity problem F322 exposed. An accession can identify a filing to inspect,
but does not restore information omitted by a flattened fact row.

Separately, filtering historical submissions on whether they were subsequently
amended could use later information. This is an inference from prevrpt's meaning,
not an observed QuantForge leak. A causal reconstruction would need an explicit
availability/timezone policy and amendments admitted only when available.
Neither accepted alone nor the dataset's current publication proves every
transformed field was observable at that historical decision time.

**Result: FSDS alone is not a verified drop-in source for this exact historical
panel.** Do not build a qtrs==4/month-end adapter and call it the reviewed PIT
policy. This conclusion does not rule out a separately reviewed FSDS accession
index supplemented by original contexts, historical security identity and
consistent value-price/share inputs. Current ADR423's opt-in refuses priced
records; supplying rounded numbers to it does not complete combined_score.

No such reconstruction or experiment is adopted here. Any future integrated
source proposal must establish those identities and sufficient causal score/price
rows before an economic claim; a parser-only fragment would not close this gap.
No ADR, runtime change or synthetic test is needed for this source review.

## Economic accounting and next observation

Fresh read-only reports: 3,314 experiments, 7,103,306 lifetime candidate trials,
279 graduate experiments/41 names, zero ADR018 survivors. Paper retains44
positions (7open/37closed), zero mature at126 bars, maximum86 bars. Its all-book
median paired configuration return remains −1.82729047percentage points;
these unequal-horizon retrospective scores are not account alpha.

New economic trials/configurations/source attempts: **zero**. All previous
selection accounting remains; no effective-N reset or uncertainty estimate.
No gross/net strategy economics or financial gates were measured here. Acceptance
was source sufficiency for the existing exact contracts, not attractive returns.
The documentation comparison failed that sufficiency condition; it did not test
whether quality/value earns money. **The alpha case did not improve.**

The next already registered economic experiment remains ADR418's sole final
screen, only [2027-02-11T00Z,2027-02-12T00Z): fixed83/412,64closes/63intervals,
fixed units,10bp entry+exit, eligibleEW/SPY/cash controls and exact strict positive
net excess against all three. Full gates remain NOT MEASURED even on screenPASS.
No interim look, new source substitution, retry, reroot or threshold change.
ADR416/417/422/SIC and all older cohorts/timing roots remain frozen.
