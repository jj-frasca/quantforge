# ADR-325: Measure restricted cross-sectional purged diagnostics

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Codex autonomous session 3, ISO 2026-W43
- **Extends:** ADR-024/039/078/104/145/150/198/291/293/321/322
- **Addresses in part:** FINDING-265
- **Preserves:** FINDING-272's rolling numerical-support limitation

## Context

Family walk-forward is measured and published; panel purged CV still records
geometry without scores. FINDING-272 prevents promoting rolling-window lengths
to exact computational source-isolation claims. A coherent first domain can
use only audited direct-shift price factories, with explicit unmeasured outcomes
for everything else and family-specific benchmark pairing.

Current factories are freshly created lambdas. Names or matching grids cannot
certify a callable, and comparing two independently constructed lambda objects
cannot identify ordinary shipped factories. Durable geometry must also validate
without allocating arrays from arbitrary persisted bar/fold counts.

## Decision

Initially support xs_momentum, xs_reversal and xs_short_term_reversal_1m only,
for native Float64 complete positive panels and their shipped signal parameter
combinations. Make their factory callables stable module-owned functions,
retaining precisely their existing int coercions and returned signal formulas.
Require both recognized family identity and exact known factory object identity;
replaced same-name factories remain unsupported. Unsupported price dtypes or
parameter domains remain eligible for primary search with explicit unmeasured
PCV, never an invented zero lag. Static maps and rolling factors are deferred.
This protects accidental substitution, not malicious Python global mutation.

Use the actual allocated configs, including every searched quantile, without
rerunning signals or changing allocation. Momentum signal operands reach L+S
price rows back; reversals reach L. Net return t uses current and previous ranked
weights and asset returns, so the conservative direct-price hull is [t-D,t],
D=L+S+1 or L+1. Family D is the maximum over allocated configs, not the unallocated
catalog. Set E=max(original user floor,D); never shrink it to fit. Validate the
original floor and requested-fold counts through require_trial_count (minimum0
and2), after existing prior_trials validation. Coercible float/bool counts become
unsupported request evidence, an explicit completed-run domain tightening.

Symmetric E=D separates these direct operand hulls on both sides of each test
block. E=D-1 can share the oldest endpoint with left training and the last test
price with right training. This is source-operand separation for the restricted
recipe, not statistical independence, universal floating precision, economic
isolation or causal training. PCV intentionally selects on later training rows. The eventual winning family
still uses the whole search sample; this statistic does not evaluate train-only
cross-family selection.
Bounded direct probes cover all12 shipped signal configs and36 portfolio configs;
they supplement the operator derivation without certifying arbitrary code/dtypes.

For each allocated family, reuse unchanged purged_kfold_splits and
purged_cv_evaluate on the existing complete return matrix. Pass the already
search-only equal-weight universe return benchmark. Persist its same-evaluator
mean over that family's actual retained test folds; there is no experiment-wide
PCV control because different E can keep different fold populations. Existing
fixed-config warmup/internal costs continue; account entry/switch trades and
stitched-policy Sharpe are not modeled. The benchmark has no added turnover cost.

Add a nullable frozen, always-revalidated per-trial purged diagnostic with a
recognized method, explicit measured/unsupported/no_usable_folds status, actual
search bars, requested folds and floor. Unsupported outcomes record a recognized
reason and no support/score claim. Supported outcomes record dependency rule,
maximum allocated D, exact E and kept fold ordinals. Measured outcomes require
finite mean and paired benchmark plus positive kept geometry; no-usable-fold
outcomes have empty kept ordinals and no scores. Bind the inherited
purged_cv_oos_sharpe exactly to the measured nested mean; unmeasured current
branches require it null. Absent entire evidence remains legacy and permits
historical unpaired scalars without invented method or geometry.

Validate original integral metadata and kept geometry with Python integer
arithmetic, without generating arrays. For q,r=divmod(N,K), test j starts at
q*j+min(j,r) and ends after q+(j<r) rows. It has training iff start>E or end+E<N.
These form a prefix union suffix; two binary searches determine exact cardinality.
Strict sorted unique in-range ordinals, cardinality and membership prove the
complete kept set with O(logK+m) time and O(1) extra geometry space. Construction,
unchecked nested copies, experiment reconstruction and stores share this boundary.
If any trial carries current PCV evidence, require complete same-request evidence
on all trials, and bind its bar count to attributed WF geometry when present.
Compact evidence cannot independently replay all allocated configs or prove source
provenance; actual producers establish the allocated maximum and measured means.

Attach full measured results and actual kept count to ephemeral reports. Current
unmeasured outcomes use null/count0 with explicit status flags. Legacy historical
geometry-only counts retain their attribution. No usable folds is a preflight
geometry outcome; other evaluator errors propagate, not a catch-all ValueError
label. Complete matrix/benchmark validity must precede unmeasured shortcuts
(existing primary/WF validation already supplies this boundary). Measurement
can refuse a formerly successful run if real evaluator arithmetic is unmeasurable.

The gate-bearing estimates, winner, whole-search pricing/PBO, lifetime accounting,
holdout and every threshold stay exact on measurable controls. Longitudinal v14,
calibration cohorts and generated files remain unchanged. This backend slice
publishes no new API fields or scores. Correct only the panel's global PCV caption
to say results are not published there; claiming all backend PCV is unmeasured
would become stale. Full attributed API/UI publication is a separate slice.
FINDING-265 remains open for unsupported families and public PCV publication.

## Alternatives and reversal

1. Restricted measured recipe with durable unsupported outcomes: chosen, useful
   without claiming rolling numerical history has finite isolated support.
2. Integrate every family using max-grid integer or nominal windows: rejected
   by hidden defaults/composition and FINDING-272's executable counterexample.
3. Add an unused metadata resolver: rejected; does not close measurement.
4. One global maximum embargo/control: rejected; unnecessarily destroys short
   family geometry and hides family pairing differences.
5. Name-based certification or caller tags: rejected; do not bind the factory.

Reverse producer measurement and stable wrappers together, retaining already
persisted evidence readers and written findings. Never rewrite generated rows.
A new family, support basis, selector, estimator or public score publication needs
separate reviewed evidence. No source/cohort/calibration search is authorized by
this implementation beyond deterministic synthetic unit/control fixtures.

## Verification

Observe backend and caption RED before their source edits. Require replaced
same-name/custom/rolling/static/unsupported-dtype/config outcomes, allocated maxima,
both source-support endpoints, selected-test/first-tie scoring, differing kept
folds and paired benchmarks, no-fold status, numerical failure propagation,
holdout exclusion, legacy/immutable JSON graph and forged store-copy refusals.
Hypothesis covers geometry and bounded financial selection/source invariants.
Freeze exact primary payloads and core hashes before implementation. Preserve all
primary fields except new diagnostic evidence, inherited PCV scalar and run UUID/
time; preserve WF, gate and calibration identities. Compare wrapper outputs to
original factory baselines. Independently review, run foreground make check-all,
commit explicit paths, fresh fetch/rebase, push individually and verify exact CI.
