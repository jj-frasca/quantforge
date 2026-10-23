# ADR-347: Read versioned high-proximity purged evidence before production

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Codex autonomous session20, ISO2026-W43
- **Extends:** ADR-325/327/328/346
- **Related:** FINDING-265/272

## Context

The restricted PCV method identifies direct-shift families. A prospective fixed
trailing-high recipe cannot honestly reuse that identity. Source inspection of
pandas3.0.6 Cython rolling max supports window-local operand selection on complete
native Float64 panels; the portfolio's previous weights extend the signal window
one row, giving the conservative net-return hull [t-W,t]. This is not the
sum/variance recipe in FINDING-272. Numba runtime and future versions are unaudited.
No rolling measurement is adopted here.

All current readers require one method across families, although family-specific
dependency recipes, embargoes and paired controls already differ. A producer that
changed only high-proximity attribution would fail experiment/API/client loading.
Install and verify compatible readers first, before a separate producer decision.

## Decision

Add the exact family method
`restricted-pandas-3.0.6-cython-high-purged-equal-weight-continuation-v2`
and dependency rule `rolling-high-v1`. Retain the existing shift method and its
default exactly. New-method evidence is supported measured or no_usable_folds
only, requires the new rule, and has maximum allocated lag in126/189/252. Old
methods cannot carry the new rule. Unsupported outcomes keep the old method and
reasons; no prospective engine refusal vocabulary is added.

Full trial reconstruction additionally binds new-method evidence to xs_52w_high
with exactly window/quantile finalist parameters, nonboolean Integral
window after the inherited Trial parameter normalization in126/189/252 and maximum allocated lag at least that window. Existing
shift-domain checks remain unchanged. Trial parameter coercion is not replaced;
NumPy integers normalized to floats by that inherited union still refuse, as
with the shifted-family parameter boundary. Preserve all original numeric, scalar,
branch, embargo and allocation-free kept-geometry validation. These readers
validate attributed claims; they cannot certify a claimed engine actually ran.

Allow these recognized family methods to coexist within one experiment, API
view and parsed client view. Continue requiring every current family outcome,
common search bars/requested folds/original floor, attributed WF-bar agreement,
scalar binding and each family's complete geometry and paired means. Remove
only method equality from the common request; unknown methods still refuse.

The client retains the new identity exactly and renders the existing paired
means and fold details, with a human-readable pandas3.0.6/Cython trailing-high
qualification for that method. General caption refers to audited family recipes;
all later-training, whole-sample family selection, PIT, mean-of-Sharpes and
account-switching limitations remain. Do not display raw method/rule identifiers.

Do not modify support_lag, measure_family_purged, report assembly, signals,
registry, allocation, scores, gates, thresholds, fingerprints, v14 or generated
records. xs_52w_high remains unsupported by every actual producer. A later ADR
must adopt an engine/version/domain refusal policy and independently audited
runtime/source-endpoint evidence before producing new-method measurements.

## Options considered

1. Reader-first family attribution: chosen; mixed-method full-graph fixtures
   make the compatibility step reviewable, at the cost of an unused producer
   branch until a separately reviewed follow-up.
2. Reuse the shifted-only method: smaller but misstates the scientific recipe.
3. Replace every family's method with one generalized version: avoids mixed
   methods but needlessly relabels unchanged shift/unsupported evidence.
4. Couple producer adoption and readers: fewer commits, but combines a new
   scientific execution domain with persistence/client compatibility.

## Verification and reversal

Observe backend and client RED before source edits. Exercise measured/no-fold,
new/old method-rule mismatch, wrong lag/family/finalist, mixed full experiments,
store and API projection, unknown methods and unchanged request/scalar/WF refusal.
Retain all old tests and producer behavior. Require independent research/frontend
review, exact prior producer AST and unrelated bytes/fingerprints, foreground
make check-all, individual push and exact master CI.

Reverse new reader branches and restore request method equality before any
producer adoption. Preserve historical readers and generated evidence after a
future producer ships; never rewrite data to reverse a reader decision.
