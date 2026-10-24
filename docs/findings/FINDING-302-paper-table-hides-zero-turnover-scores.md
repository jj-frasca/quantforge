# FINDING-302: Paper table hides served zero-turnover scores

- **Date:** 2026-10-24
- **Status:** Resolved by ADR-362 for affirmative served score/curve evidence
- **Area:** PaperPortfolioTable and forward-score schema comment

At `7bf871e3`, PaperPortfolioTable marks every positive-bar score with zero
forward_trades as unmeasured. It replaces both strategy Sharpe and return with
dashes and removes server comparison styling, even when those served quantities
are nonzero. The existing singular-grammar fixture itself supplies count0 with
Sharpe0.9/return0.08 while expecting an unmeasured label. ADR-361's independently
reproduced public inherited-short score also has count0 and nonzero measured
returns; the display still conceals them.

A subsequent exhaustive read-only census of current `data/paper_portfolio.json`
found 44 retained scores, 33 explicit integer zero counts and 11 nonzero counts,
with no absent counts. Ten zero-count records have both nonzero strategy scalars
and nonunit strategy curves (nine closed, one open); the existing predicate hides
their supplied strategy metrics. The open QQQ/coppock_curve row carries 56 bars,
return -0.01694702310323115 and Sharpe -0.39481000337318684 with count zero.
Independent Decimal and binary64/display-domain censuses agree. File SHA256
before/after is `5a4a61638af4d0602697927cedab747f990a7e0201ce54beb2b04005ea75359c`
(547195 bytes). Receipt: `/tmp/qf-w43-s29-zero-count-score-census.json`.
These are retained metadata observations only: no original-return, exposure,
execution, code-provenance or broker-loss attribution follows. No data was edited.

Zero position changes cannot certify absent exposure. Nor can the historical
default-zero count establish original execution. The frontend has no original
return series; it can preserve affirmative evidence from served strategy scalars
and any nonunit strategy-equity point without reconstructing that source.
Round-trip curves matter even when both scalars are zero. Benchmark movement
does not establish strategy-return evidence. Zero scalars and unit/empty curves
remain ambiguous, so their copy must describe absent recorded evidence rather
than declare that a strategy never held exposure.

ADR-362 specifies this bounded presentation-only correction, keeping supplied
scores, counts, server verdicts and schema expressions unchanged. Independent
prospective frontend review approved the scope.

Before implementation, 12 cases genuinely failed with seven preserved cases;
an initial test.each fixture-shape error was corrected before that RED run and
before source edits. All 19 table tests then passed, including ten new cases,
independently reproduced by the frontend reviewer. A weak combined negative CSS
assertion was strengthened before the full gate's frontend step. Final frontend
review approved the bounded predicate, legacy copy and server-verdict handling;
independent research review approved the census paragraph without another look
at generated data.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 14,575 backend and 746
frontend tests, at 97.41% backend coverage and 97.88% frontend statements, with
lint/format/types green. The entire frontend schema remains byte-identical after
full-line comments are removed; backend paper code and the IC panel are unchanged.
Receipts: `/tmp/qf-w43-s29-check362.log` and
`/tmp/qf-w43-s29-paper-display-preservation.json`. No scores, flags, counts,
thresholds, original returns, generated records or frozen cohorts were rewritten.
