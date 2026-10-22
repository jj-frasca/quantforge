# FINDING-291: About page overstates validation scope and null PBO behavior

- **Status:** Resolved — About reporting correction; source-docstring follow-through remains separately scoped
- **Date:** 2026-10-21
- **Severity:** Medium — public interpretation differs from the implemented diagnostic
- **Reviewed revision:** `e1cc3086`
- **Related:** ADR-039/105/293; FINDING-246/272

## Evidence

AboutPage describes CSCV as splitting the configuration grid, rather than time
observation groups, and says a random walk gives PBO approximately 0.5. The
implemented statistic ranks configurations on balanced splits of observations;
candidate dependence and ties matter. A deterministic supplied 12-by-3 matrix
with identical candidate columns gives PBO 1.0 with four groups. This is a
bounded tie/control example, not a random-walk simulation, null error-rate
estimate or contradiction of an explicitly specified exchangeable null model.
It does not support a fixed value for every random walk or candidate set.

The page also says purged CV removes overlapping labels and an embargo after
each fold prevents look-ahead. The implementation excludes row neighborhoods
on both sides of each test block and selects configurations using the retained
training rows, including later observations. With 12 rows, three folds and
embargo 1, the first test is rows 0..3 and training is 5..11; the middle test
is 4..7 and training is 0..2 plus 9..11. There is no label-interval overlap
analyzer. ADR-039 defines the embargo as a largest-integer-parameter lookback
proxy; it does not certify source independence. FINDING-272 separately shows
why nominal rolling windows cannot establish exact numerical source isolation.
No longitudinal PCV numerical error is inferred from that cross-sectional witness.

ADR-293 further limits walk-forward to train-selected fixed-config continuation
window scores. Their headline is an equal mean of window Sharpes; the supplied
paths do not reconcile entry/switching trades for a single adopting account.
Past-only selection is not evidence of executable switching-account returns.

Required research and frontend scope reviews independently confirmed these
public-copy discrepancies. Deterministic receipt:
`/tmp/qf-w43-s13-about-scope.md` and `.json`. No RNG, source generator, search,
calibration, provider, broker, credential or external service was used.

## Correction and boundaries

Correct only explanatory JSX and add rendered reporting regressions. Explain
observation splits, out-of-sample ranks and the unchanged high-risk threshold;
remove universal random-walk PBO claims. Distinguish causal continuation-window
selection from purged resampling that permits later training observations, and
state the lookback-gap and switching-account limitations in user-facing terms.
Remove the stale fixed data-quality-check count and neutralize the historical
ADR-001 label while retaining the explicit paper-only scope.

Active cold memory's row-gap invariant is likewise labeled as geometry, replacing
its unqualified "no leakage" gloss. The same proxy/source-independence distinction
is stated beside its intentional later-training description. Historical numeric
tables and accepted ADR wording remain intact.

Preserve PBO/DSR thresholds, methodology calculations, server verdicts, schemas,
catalog rendering/loading/errors, links, styles and layout. No actual incorrect
graduate, production leakage incident, score change or new measurement is
established. Existing accepted ADRs and frozen/generated evidence remain intact;
this reporting correction requires no new architecture or methodology decision.

## Verification

Session13 retained actual rendered-test TDD receipts: four new regressions failed
while all four original tests passed, then all eight passed after the copy change
(`/tmp/qf-w43-s13-about-red.log` and `-green.log`). Session15 independently reran
all eight rendered tests successfully through the required frontend review.
Required frontend and research final reviews both approve the four-path scope.

Fresh session15 TypeScript AST comparison preserves every node except JSX text
and the declared ADR-001 label; all four original test bodies remain byte-identical.
The other 1,291 tracked backend/frontend/data paths match the reviewed parent
byte-for-byte. Receipt: `/tmp/qf-w43-s15-about-preservation.json`.
No scientific score, threshold, schema or generated record changed.

Fresh foreground `make check-all PYTEST_WORKERS=2` completed successfully:
13,811 backend tests, 570 frontend tests, 97.38% backend coverage and 97.83%
frontend statement coverage; lint, format and strict type checks passed.
Receipt: `/tmp/qf-w43-s15-check291.log`.

This resolves the About publication gap. Remaining active primitive docstrings
and the cold-memory PBO noise gloss require a separately verified follow-through;
this correction does not claim exhaustive cleanup of every source description.
