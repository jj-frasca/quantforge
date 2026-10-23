# ADR-348: Measure runtime-attributed high-proximity purged diagnostics

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Codex autonomous session20, ISO2026-W43
- **Extends:** ADR-325/346/347
- **Addresses in part:** FINDING-265; preserves FINDING-272

## Context

ADR-347's separately attributed high-method readers are published and exact CI
green. The actual producer still reports xs_52w_high unsupported. A fixed trailing
maximum differs from the rolling sums/variance in FINDING-272: its reviewed
pandas3.0.6 Cython kernel selects an in-window operand, without a floating
accumulator carrying expired-price arithmetic. The default engine can change
through compute.use_numba, so nominal window length alone is insufficient.

The exact tagged primary source is
[pandas3.0.6 roll_max](https://github.com/pandas-dev/pandas/blob/v3.0.6/pandas/_libs/window/aggregations.pyx#L913-L1051).
For monotone fixed-window bounds, deque indices expire before the window start.
A newer dominating operand can discard an older one safely because it expires
no earlier. The selected front operand is in the current window. Complete finite
values make the integer validity count independent of price values. Installed
rolling dispatch, FixedWindowIndexer and the standard option callback were also
reviewed. Numba runtime, arbitrary builds, future versions, custom indexers,
monkeypatched internals and hostile/concurrent global mutation are not certified.

Signal at t uses [t-W+1,t]. Previous weights and current turnover extend net return
to [t-W,t], hence D=W. For shipped W126/189/252, deterministic public portfolio
probes change only the oldest endpoint and independently observe changed gross
and turnover; t-W-1 leaves every operand at t exact. Current-price perturbation
changes current return/turnover and leaves earlier outputs exact. Direct window
max and prefix controls agree. E=W separates inclusive train/test price hulls;
E=W-1 can share both boundary prices. These controls supplement the operator
argument; they are not calibration, independence or a market-impact estimate.

Search builds all matrices before measuring PCV. Checking the global engine
only at measurement can misattribute the matrix if another family changes it.
Runtime attribution therefore belongs at actual known high-config generation.

## Decision

Support only exact shipped high_proximity_factory identity, xs_52w_high name,
native Float64 complete positive panels and allocated window parameters126/189/252
with existing nonboolean Integral parameter checks. Preserve factory coercions,
signals, ranker, allocation, matrix rows/order and all primary computations.
Other rolling/static/custom recipes remain unsupported.

Capture a frozen ephemeral HighRuntime receipt immediately before and after
each known high configuration's existing _config_returns call. Record pandas
version and, for the reviewed exact version, the standard compute.use_numba
option. Matching receipts across both sides and every allocated configuration
are required; mismatch raises ValueError because no single execution domain can
be attributed. Do not force an engine or change a global option. Only known high
factories need this observation; other families keep their existing execution.
Carry the agreed receipt alongside its matrix until PCV measurement.

At measurement, classify that saved domain, without rereading current globals.
Exactly pandas3.0.6 and compute.use_numba=False support the reviewed Cython recipe.
Other versions and engines yield explicit unsupported_pandas_version or
unsupported_rolling_engine reasons under the existing unsupported v1 branch.
Primary eligibility is unchanged for those explicit unsupported outcomes. A
missing known-high matrix receipt raises rather than inventing runtime provenance.
Direct matrix/receipt callers retain responsibility for their correspondence;
a frozen object is bounded metadata, not a hostile-code provenance proof.
Pure support_lag queries may inspect the current domain without claiming a matrix.

Use D=max(W) across actually allocated high configs and E=max(original floor,D).
Never reduce E to fit. Reuse the unchanged evaluator on the existing full family
matrix with its actual retained-fold equal-weight universe benchmark. Successful
and no-fold high outcomes use ADR-347's exact v2 method and rolling-high-v1 rule.
The three shift families retain exact v1 evidence. No-fold high evidence retains
its supported geometry and absent scores. Other evaluator errors propagate.

Extend API/client reason vocabulary and plain-language unsupported display only;
ADR-347 already handles new high scores and mixed methods. Supersede ADR-346's
blanket high-unsupported assertion with stronger exact-domain support and
unaudited-domain refusal controls; do not delete or skip the test.

PCV remains noncausal fold reselection, with whole-sample final family choice,
continued-config internal costs, no account-switching reconciliation, no extra
benchmark turnover cost, no PIT/universe-independence proof and no panel null
calibration. No threshold, selector, longitudinal v14, fingerprint, generated
file or frozen cohort changes. A new measurement failure can refuse a formerly
completed search; unchanged accepted formulas do not certify unchanged rates.

## Alternatives and reversal

1. Restricted captured-runtime support: chosen; useful and auditable, with extra
   ephemeral metadata and dependency-version maintenance.
2. Check engine only when measuring PCV: rejects/accepts based on the wrong time.
3. Force Cython globally or change high signal calls: unnecessary alteration of
   primary execution semantics, including callers opting into another engine.
4. Enable every rolling family from its nominal window: contradicted by F272.
5. Continue deferring high support: safe but leaves an audited measurable gap.

Reverse only high producer support and ephemeral capture plumbing. Retain the
published readers, written evidence and all generated historical measurements.
Future dependency/engine domains require a separately reviewed decision.

## Verification

Before source edits, observe failing tests for support/classification/required
receipts and end-to-end measurements, preserving unaudited/custom refusal controls.
Use fake receipt sequences for engine/version changes, never execute Numba.
Exercise before/after and cross-config mismatches; saved unsafe then current safe,
saved safe then current unsafe; no global reads during measurement; missing
receipt/custom identity precedence; allocated maximum, no-fold/large-floor and
numerical refusal; paired actual folds and holdout exclusion; complete mixed
store/API/client claims. Hypothesis covers financial support locality and shipped
allocated hulls. Freeze primary synthetic payloads before implementation.

Require exact original signals/portfolio formulas, unchanged three-shift evidence,
primary/WF/gate/accounting payloads and fingerprints, independent research and
frontend review, foreground make check-all, individual publication and exact CI.
No new null/power/source cohort, provider or paid service is authorized.
