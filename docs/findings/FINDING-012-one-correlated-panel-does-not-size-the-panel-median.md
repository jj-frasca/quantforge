# FINDING-012: One correlated null panel does not size the panel median

- **Severity:** High — a plausible follow-up can repeat ADR-075's independence error under a new
  generator name
- **Found:** 2026-08-30 by Codex design review of ADR-075's correlated-panel follow-up
- **Status:** ADR-081 identity, joint-row generator, and inference implemented; measurement pending
- **Affected:** ADR-075, `null-calibration.yml`, `NullCalibration`, `_clustered_difference_ci`

## Finding

ADR-075 correctly states that its interval is too narrow because 66 real symbols share one calendar
window, then calls a correlated-panel null “the fix.” Generating one joint 200-symbol null panel is
necessary but not sufficient. It provides one correlated realization of the panel median. The
current comparison would still resample the 200 resulting symbol-level excesses independently and
therefore erase the dependence the new generator was built to preserve.

The sampling distribution needed by ADR-075 is the distribution of a **panel statistic** under the
null. Estimating it requires independent panel-level replicates, each carrying the whole dependent
cross-section through the unmodified search, or a different pre-specified dependence-aware
instrument built from time/fold-level observations. Correlated columns inside one calibration do
not create those replicates.

## Evidence

- `_clustered_difference_ci` samples `null_excess` element by element with `rng.choice`; it has no
  panel identity to resample.
- `NullCalibration` stores flat finalist-diagnostic lists and no `panel_replication_id` or
  per-panel median.
- ADR-037 and `null-calibration.yml` explicitly rely on null symbols being independent and merge
  symbol shards. A correlated panel invalidates that execution assumption unless every shard uses
  the same synchronized panel draw and consolidation preserves its identity.
- One jointly row-resampled source panel yields one value of `median(null excess)`. Treating its 200
  correlated symbol values as 200 bootstrap units recreates the under-width defect rather than
  measuring between-panel variation.

## Impact

The existing ADR-075 result remains explicitly a lower bound on its own width; this finding does not
change a graduation, threshold, or generated artifact. It prevents the next implementation from
claiming that contemporaneous correlation alone repairs the confidence interval when the reporting
statistic still assumes independent null draws.

## Required design before implementation

1. Pre-state the panel-level estimand and the number of independent panel realizations needed to
   resolve a decision-relevant effect before observing their results.
2. Preserve panel identity in the artifact and resample/compare panel statistics, never individual
   correlated symbols as if independent.
3. Make the generator destroy the serial predictability catalog strategies trade while preserving
   the contemporaneous dependence being tested, and measure what joint-row resampling loses about
   persistent market regimes.
4. Replace or redesign ADR-037's independent-symbol sharding; a partial panel is not an independent
   null sample.
5. Do not dispatch the expensive repeated-panel experiment under a no-cloud/no-billable-runner
   mandate. Code mechanics can be tested locally, but no headline changes without the authorized
   full measurement.

## Accepted design

ADR-081 freezes the missing design without spending the measurement: equal weight per real symbol,
joint iid resampling of complete calendar vectors, 400 independent whole-panel replicates, exact
source/cohort/search identity, and a separate manual workflow sharded only by complete panel index.
The ADR-075 headline and lower-bound qualification remain unchanged until an authorized completed
artifact is interpreted under a later ADR.

The first implementation slice is intentionally non-measuring: `panel_null.py` makes the whole
panel an indivisible, globally indexed artifact and refuses partial/mixed consolidation. It does not
compute tail inference, dispatch a workflow, or change the headline. Direct final-artifact
construction enforces the same complete-panel invariants, and all persisted real/panel statistics
must be finite.

The deterministic generator primitive now consumes an already aligned complete source panel, draws
one iid sequence of whole calendar rows, shares it across every symbol, and reconstructs each OHLCV
path with the selected row's geometry. Source preparation now freezes an explicit ordered cohort,
the most recent exact complete-case calendar, and a canonical digest before generation. ADR-082
freezes and implements pure tail inference over a complete artifact, including simultaneous exact
binomial uncertainty. Real cohort selection now matches exact search/gate/history identity, uses the
persisted finalist, rejects duplicate experiment IDs, and collapses repeats to one median excess per
canonically ordered symbol for eligibility. ADR-085 then applies the same checked production search
once to each exact observed prepared-source column and replaces those pool-derived values before
inference. The binding boundary refuses symbol-order or target-history drift before
freezing that selection with the prepared panel's exact source identity, 400 replicates, and the
selected effective-symbol floor. A local injected fetch boundary now requests every frozen symbol
once in canonical order and reports all provider failures before preparation; network adapter/date
wiring is supplied by the production preparation command described below. A complete-panel runner
now jointly generates all symbols, calls an
injected search once per symbol, rejects returned experiment-identity drift, and preserves failures
inside one panel statistic. Its production adapter rejects search/gate policy drift before returning
a direct wrapper over unmodified `run_search`; tests alone inject a stand-in. The prepared source
can now be written once to an exclusive-create, pickle-free compressed archive and loaded by a
future batch without trusting its stored digest: exact fields, UTC-nanosecond calendar, array shape,
and canonical digest are revalidated after reconstruction. The local batch boundary loads that
archive, executes only explicit unique in-range global panel indices as complete panels, and
exclusively creates one validated scratch shard. Direct construction and reload both reject seed,
index, panel-identity, error-accounting, and symbol-floor drift. The complete cohort identity now
crosses the future preparation/batch boundary in an exclusively created JSON manifest that is
revalidated on both write and read. The local production-batch driver loads the manifest and source
archive as one frozen job identity before constructing the checked search adapter and executing the
requested whole-panel indices. The consolidation CLI loads and revalidates every scratch shard,
requires all frozen global indices, prints the fixed ADR-081/082 inference, and is the sole writer
of the optional final artifact. The production preparation CLI now pins one explicit UTC cutoff
across the frozen cohort, uses the shared cloud retry policy, and writes only immutable scratch
source/manifest inputs while refusing repository `data/` paths. The production batch CLI accepts
exactly one explicit unique index set or half-open global-index range, refuses existing or
repository-`data/` shard paths before expensive execution, and delegates the frozen inputs plus
current production policy to the checked whole-panel driver. The manual-only workflow now carries
one prepared input pair through 40 disjoint complete-panel batches and permits only full validated
consolidation to write the generated result. It has not been dispatched, so no measurement exists.
No generated artifact has been written and the
headline is unchanged.
