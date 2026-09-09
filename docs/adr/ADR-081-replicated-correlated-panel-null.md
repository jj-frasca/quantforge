# ADR-081: Measure the excess statistic with replicated correlated null panels

- **Status:** Accepted; cohort/source selection, fetch orchestration, preparation, binding, identity, generator, replicate execution, and inference implemented;
  measurement pending
- **Date:** 2026-09-01
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-012, ADR-075
- **Relates to:** ADR-030, ADR-037, ADR-064, ADR-067, ADR-068, ADR-078, ADR-080

## Context

ADR-075 resamples real experiments by symbol but resamples null symbols independently. The real
symbols share one calendar window, so market-wide shocks make their excess diagnostics dependent.
The resulting interval is explicitly a lower bound on its own width.

FINDING-012 rules out the superficial repair. One jointly generated null panel supplies one draw of
the panel median. Feeding its correlated columns back into an elementwise bootstrap erases the
dependence again. The sampling unit must remain the whole panel through generation, storage, and
inference.

There is a second mismatch to remove before measuring. The current real median contains every
matched experiment, so a symbol searched repeatedly receives more weight. A generated panel
naturally supplies one search per symbol. Comparing those two statistics would mix panel dependence
with run-frequency weighting.

The resampling basis follows Efron's bootstrap over vector observations (Annals of Statistics 7,
1979, DOI `10.1214/aos/1176344552`): one observation here is the complete same-day return vector,
not one symbol return. Politis and Romano's stationary bootstrap (JASA 89, 1994) is not the null for
this question because retaining time blocks also retains the serial structure the catalog trades.

## Decision

Build a **separate panel-null instrument**. ADR-037's independent-symbol artifacts remain the
Type-I calibration of the gate and are neither overwritten nor reinterpreted.

### 1. Freeze one equal-symbol estimand

For a diagnostic `d`, define each real symbol's value as the median of that symbol's matched
experiment excesses, then define the panel statistic as the median across symbols:

`T_d = median_symbol(median_repeat(d_oos - d_hold))`.

Every symbol therefore has weight one. The primary pre-registered diagnostic is causal
walk-forward excess. Purged-CV excess is stored and reported as a secondary diagnostic; it cannot
silently replace or pool with the primary result.

The cohort is frozen before generation by:

- ordered symbol list;
- search and gate fingerprints;
- target history and ADR-064 tolerance;
- completed source start/end dates; and
- the exact real per-symbol values used in `T_d`.

Fewer than 30 measured symbols fails before generation, matching ADR-067/075. No pool-wide fallback
is allowed.

### 2. Generate one null panel by jointly resampling calendar rows

Fetch the frozen symbols once, align them on completed common timestamps, and retain exactly the
target number of most-recent complete rows. Missing values are never imputed. If the complete
calendar cannot supply the target history, the preparation step fails and reports the excluded
symbols; changing the cohort requires a new artifact identity.

For panel replicate `r`, draw one iid sequence of calendar-row indices with replacement from the
aligned source panel. Apply that same index sequence to every symbol's close return and same-bar
open/high/low/volume geometry, then reconstruct each price path. This preserves the empirical
contemporaneous joint distribution of the complete panel while destroying calendar ordering and
therefore serial predictability. Each generated symbol passes through the unmodified production
search and its own paired walk-forward/purged-CV benchmark.

The unit emitted by a replicate is one immutable `PanelNullReplicate` containing `panel_id`, seed,
successful symbol count, errors, and the two equal-symbol panel statistics. Per-symbol diagnostics
may be retained for audit but are never resampled as independent observations.

### 3. Use 400 independent whole-panel replicates

The measurement uses exactly **400** pre-indexed panel replicates. This gives ten expected draws in
each 2.5% tail and Monte Carlo p-value resolution `1 / 401`. Seeds derive only from the base seed and
global panel index, so batching cannot change the sample.

For walk-forward excess, report:

- the real `T_d`;
- the null-panel median and 2.5th/97.5th percentiles;
- both fixed tail counts, `count(T_null <= T_real)` and `count(T_null >= T_real)`;
- the plus-one two-sided Monte Carlo p-value,
  `min(1, 2 * min((1 + lower_count) / 401, (1 + upper_count) / 401))`; and
- an exact binomial confidence interval for each tail probability's Monte Carlo uncertainty.

The tail thresholds are the fixed observed `T_real`, so each count is binomial across independent
panels; neither count is centered on an estimated null median. A future headline may call the panel
result separated only if one tail interval lies wholly below **0.025** (Bonferroni two-sided 0.05).
It may call it not separated only if both tail intervals lie wholly above 0.025. Otherwise the fixed
400-replicate experiment is **unresolved**. Extending it after seeing the result requires a new ADR;
an ad hoc extra batch would be an unpriced third look.

The existing ADR-075 interval and all three qualifications remain unchanged until a later ADR
interprets a completed panel artifact. This decision designs an instrument; it does not spend its
measurement or move a threshold.

### 4. Preserve source and panel identity through execution

Use a new manual-only `panel-null-calibration.yml`, not ADR-037's scheduled independent-symbol
matrix. A preparation job writes one immutable workflow artifact containing the aligned source
panel and its SHA-256 digest. Batch jobs download that exact artifact and process disjoint global
panel indices; they never split a panel across jobs. Consolidation rejects:

- a missing or duplicate panel index;
- fewer or more than 400 completed indices;
- any source-panel, cohort, search, gate, history, generator, or diagnostic-version mismatch; and
- a replicate below the frozen effective-symbol floor.

Only consolidation may write `data/panel_null_calibration/`, under ADR-030. The committed artifact
stores summaries and identities, not the fetched source prices. The workflow is dispatch-only
because it is expensive and is rerun only after an explicitly reviewed identity change.

No workflow is dispatched by this ADR. Local tests use tiny deterministic panels and scratch paths.

### Implementation progress

`app/research/lab/panel_null.py` now defines the frozen cohort, per-symbol real values, complete
panel replicate, shard, and consolidated artifact contracts. The cohort identity includes the base
seed, fixed replicate count, effective-symbol floor, ordered symbols and their exact real values,
source digest/dates, history rule, both fingerprints, and generator/diagnostic versions.
`merge_panel_null_shards` derives the expected global index set and symbol floor from that identity,
sorts complete panels deterministically, and rejects identity drift, missing/duplicate indices,
duplicate panel IDs, non-derived seeds, unknown/duplicate error symbols, and any panel that does not
account for the whole frozen cohort. `PanelNullCalibration` applies those same invariants during
direct construction, so deserializing a purported final artifact cannot bypass consolidation, and
every real-side or replicate statistic rejects NaN and infinity. Source fetching, search
execution, scripts, the manual workflow, and the sole-writer artifact remain unimplemented.

`joint_iid_panel_null` implements the first generator boundary on an already frozen, aligned source
panel. It rejects missing, misaligned, non-finite, non-positive, or geometrically invalid OHLCV
inputs; derives one seeded iid sequence of complete calendar-row indices; applies that exact sequence
to every symbol; and reconstructs each path from the selected close returns plus same-row
open/high/low/volume geometry. Tiny deterministic tests recover the identical selected source row
from both symbols and verify every reconstructed return and ratio. `infer_panel_null` now applies
the pre-registered equal-symbol statistic, inclusive tail counts, plus-one two-sided p-value, and
ADR-082's simultaneous exact confidence construction to a complete artifact. Purged-CV remains
unmeasured unless the complete real cohort and every null panel carry it.

`prepare_panel_null_source` now implements the non-network preparation boundary. The caller supplies
the explicit ordered cohort and one fetched OHLCV frame per symbol. Preparation rejects missing,
unexpected, or duplicate symbol identity; intersects timestamps across the whole cohort; drops only
jointly incomplete rows; retains exactly the most recent `target_n_bars`; and fails rather than
shrinking the requested history. It records the exact retained UTC calendar range and hashes a
versioned canonical byte stream containing the ordered symbols, UTC nanosecond timestamps, fixed
OHLCV column order, and big-endian float64 values. Input and exported frames are defensively copied,
so caller mutation cannot change the source identified by the digest. Fetching, real-cohort
selection from the pool, running the unmodified search, scripts, workflow dispatch, and measurement
remain unimplemented.

`select_panel_null_cohort` now implements the pre-fetch real-side boundary. It accepts only
experiments matching the exact search and gate fingerprints and ADR-064 history band, resolves the
persisted production finalist under ADR-079, collapses repeat searches to one median excess per
symbol, and sorts the full measured cohort canonically. Missing primary pairs are excluded before
the fixed 30-symbol floor; duplicate experiment identity fails closed rather than silently
reweighting a repeat. Purged-CV remains nullable per selected symbol.
`bind_panel_null_cohort` then requires that selection and the prepared panel have the exact same
ordered symbols and target history before it creates the final identity. It carries forward the
measured excesses, source dates/digest, both fingerprints, and versions; fixes the pre-registered
400 replicates; and uses the selection's effective-symbol floor for every panel.
`fetch_panel_null_source` calls an injected frame provider exactly once for every frozen symbol in
canonical order, collects all provider failures before aborting, and passes only a complete fetched
mapping into source preparation. Network-adapter and end-date wiring remain in the future manual
driver; production search wiring, scripts, workflow dispatch, and measurement remain unimplemented.

`run_panel_null_replicate` implements one complete-panel execution unit behind an injected search
callable. It revalidates the prepared source against the frozen cohort, derives the global-index
seed, jointly generates every symbol, and accepts a returned experiment only when symbol, history,
search fingerprint, gate fingerprint, and paired causal diagnostic match the cohort. Search errors
remain attributed to their symbols; the primary panel statistic is the equal-symbol median over
successful searches, while the secondary statistic is absent if any successful result lacks its
pair. The future driver must wire this callable directly to the unmodified production `run_search`;
scripts, workflow dispatch, and measurement remain unimplemented.

## Alternatives considered

1. **One correlated panel followed by symbol resampling.** Rejected by FINDING-012: it recreates
   the independence error at inference time.
2. **Keep repeat experiments as separate real observations.** Rejected: run-frequency weighting
   has no analogue in a one-search-per-symbol panel and is not the estimand of interest.
3. **Stationary or moving-block resampling.** Rejected for the null: blocks preserve serial
   structure and can preserve the very edge being tested. Joint iid calendar rows preserve the
   contemporaneous vector while destroying its order.
4. **Split one panel across symbol shards.** Rejected: it makes a partial panel look like a sample
   and permits source drift across jobs. Shard by complete panel indices instead.
5. **Replace ADR-037 artifacts.** Rejected: gate Type-I error under independent null symbols and
   the sampling distribution of a correlated panel statistic are different instruments.
6. **Increase replicates after inspecting an ambiguous result.** Rejected as optional stopping.
   The fixed design reports unresolved and requires another pre-stated decision.

## Consequences

- The new artifact answers the shared-calendar limitation at its actual panel sampling unit.
- Equal-symbol weighting removes a latent mismatch before any expensive measurement is observed.
- Complete-case alignment makes the target universe narrower and carries current-universe
  survivorship; both are explicit artifact identity, not population claims.
- Four hundred full-panel searches are expensive. The workflow remains manual, public-runner only,
  and must not be dispatched when cloud or billable runners are outside the session's authority.
- No gate, validation threshold, production selection rule, or generated data changes here.

## Reversal

Delete the future panel-null model, workflow, and generated directory. ADR-037's Type-I artifacts
and ADR-075's explicitly qualified interval remain valid and unchanged.
