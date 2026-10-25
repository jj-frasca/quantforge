# FINDING-306: Zero-bar scores dilute forward cohort means

- **Status:** Corrected by ADR-366
- **Date:** 2026-10-24
- **Severity:** Medium — an unobserved placeholder changes reported forward performance
- **Scope:** `deflation_cohorts` measured-score inclusion
- **Prior art:** ADR-033, ADR-166, ADR-361 / FINDING-301

## Evidence and limits

`_mean_forward_sharpe` includes every present score, even the zero-bar placeholder
returned before forward observations accrue. An absent score is excluded. These
two equally unobserved states consequently change the reported cohort mean.

Independent ordinary finite witness using valid supported legacy score forms:
a measured four-bar score with Sharpe4 plus an absent score yields mean4.
Replace that absent score by a zero-bar/zero-Sharpe placeholder and the mean
becomes2. A one-position unscored cohort reports `None`, while a zero-bar-only
cohort reports0. Cohort membership counts do not change. No new forward
observation justifies either change in reported performance.

This is a summary inclusion issue, distinct from zero turnover. Positive-bar
scores can carry inherited-exposure returns with zero trades under ADR-361 and
must remain included. Legitimate measured Sharpe0 also remains an observation.
ADR-033's separate research trigger requires20 positions per cohort with126
forward bars; it does not prescribe126 bars for the descriptive mean. Its
zero-bar inclusion policy was not explicit, so this correction is a new measured
sample clarification, not a claim of an earlier explicit filter requirement.

The API pool report and CLI consume these summaries. The current frontend
headline does not render the means; no visible UI-mean defect is claimed. No
current book census, affected historical report, broker action, calibration or
false graduation is established. The separate finite-sum overflow issue remains
outside this inclusion correction.

## Correction and verification

Include a score only when present and `forward_bars > 0`. Keep membership counts,
unknown-verdict exclusion, caller-selected population and native unweighted mean
arithmetic. Preserve positive-bar scores regardless of trade count, small sample
size, measured zero, empty legacy curves or absent evidence. With no observed-bar
scores the mean is `None`; do not invent a zero, a126-bar threshold or execution
history. Persisted scores, thresholds, schemas and all generated records stay.

Seven regressions failed before implementation while13 controls passed. After
the single added inclusion predicate, all54 focused tests pass, including20 new
tests and a Hypothesis invariant that unobserved placeholders cannot change a
measured mean. Independent final research review approves all six paths,
independently passes the20 new tests, and exactly reproduces88 prior summaries
on the unchanged domain of absent or positive-bar scores. Those controls cover
membership/unknowns, trade0/1, bars1/4, measured zero, present/absent evidence,
empty/unit curves and native finite arithmetic. Caller inputs remain unchanged;
removing only the added predicate restores the entire prior module AST.

Full foreground `make check-all PYTEST_WORKERS=2` passes:14,675 backend and746
frontend tests,97.41% and97.88% statement coverage respectively, lint, format and
strict typing. No numerical overflow repair, threshold, schema, accounting-v14,
generated record or frozen cohort changes are included.
