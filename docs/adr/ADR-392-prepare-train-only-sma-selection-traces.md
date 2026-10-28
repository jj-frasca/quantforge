# ADR-392: Prepare train-only SMA selection traces

- **Status:** Accepted
- **Date:** 2026-10-28
- **Deciders:** Codex autonomous session11, ISO2026-W44
- **Relates:** ADR-048/391; FINDING-332 remains open for nested evaluation

## Context

F332 demonstrates that a realized refined grid can depend on observations after
an early walk-forward window. Before building a nested diagnostic, isolate the
adaptive selection operation behind an interface receiving training prices only.
The session10 train58 control establishes exact coarse/refinement primitive rules,
not a nested estimator or complete production replay.

## Decision

Add an unused research-only `select_sma_on_train` helper in `lab/sma_selection.py`.
It receives only the caller's training frame and explicit budget, n_per_param,
refine, span and cost settings. Scope is the shipped single SMA family and native
Float64 positive finite close prices on a unique ascending calendar. Generic or
naive ordered indexes remain supported; source provenance, PIT availability and
whether the caller actually supplied a train prefix are not certified here.

Validate original nonboolean Integral budget/n_per_param (>=1), boolean refine,
finite nonboolean real nonnegative span/cost, nonempty frame, unique columns and close domain
before scoring. These are this research helper's declared narrower boundaries,
not new production input rules. Use the existing catalog allocator, grid builder,
space-filling reducer and BacktestEngine with explicit costs. Score every coarse
candidate using engine metrics, choose the first maximum, generate refinement
around that center, and score it only when >=2 budgeted candidates survive.
Compare coarse then refined candidates by the same first-maximum rule. Do not
use WF's separate Sharpe implementation for train ranking, filter zero-warmup
candidates or deduplicate hypotheses across passes. Keep singleton histories valid.

Return frozen dataclasses containing immutable primitive candidate records and
a tuple trace: pass, fast/slow, engine Sharpe, coarse center/selected ordinals,
raw/budgeted/evaluated refinement counts, reserve and normalized settings.
Derived hypothesis and engine-call counts both equal the number actually scored
in this helper; reserve and skipped refinement are not evaluations. This helper
performs one engine call per scored hypothesis. Later evaluation/control calls
must be accounted separately. Counts are not a lifetime/DSR correction.
Any acquisition-free validation, budget, strategy or arithmetic error aborts the
whole call. No partial trace, zero substitution or candidate dropping on failure.
An empty or ineligible allocated family refuses before engine calls.

No caller, CLI, artifact writer, outer WF score, new PBO, gate verdict, graduate,
production selector replay, performance improvement or calibration claim is added.
No production source, threshold, search fingerprint, v14, generated record or
frozen cohort changes. Subsequent outer evaluation needs its own design and TDD.

## Alternatives considered

1. Implement full nested WF now: deferred to keep this slice inspectable; outer
   geometry, paired scores, provenance and result validity deserve separate review.
2. Call run_search per train prefix: invokes holdout/gate/diagnostics that this
   observed-only research selector neither needs nor claims to reproduce.
3. Reuse the once-realized full-search matrix: retains F332's information boundary.

## Verification and reversal

TDD exact train58 trace, active refinement and repeated hypotheses, tied and
negative-versus-warmup scores, budget minima, scalar/frame errors, atomic failure,
actual engine-call counts and immutable output. Property tests vary unseen suffixes
while supplying an unchanged prefix and check selection independence. Compare
primitive traces against the named eae555db production rules; this is primitive
agreement, not full ValidationEngine parity. Independent research review and
foreground make check-all precede an individual safe sync/push and exact CI check.

Reversal removes the unused helper, its tests and active cold-memory contract;
retain F332 and this ADR as the record. No existing producer requires migration.
