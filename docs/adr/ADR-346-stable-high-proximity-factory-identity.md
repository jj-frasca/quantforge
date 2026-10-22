# ADR-346: Give the shipped high-proximity factory a stable identity

- **Status:** Accepted
- **Date:** 2026-10-22
- **Deciders:** Codex autonomous session19, ISO2026-W43
- **Related:** ADR-325; FINDING-265/272

## Context

FINDING-265 remains open for unsupported cross-sectional purged diagnostics.
The shipped xs_52w_high factory is a fresh anonymous function on every registry
construction. Like the direct-shift factories before ADR-325, its name or grid
cannot establish callable identity for a future restricted support audit.

A prospective source review suggests the fixed-window high-proximity factor
could be a separate support slice: on complete native Float64 panels, its
mathematical signal uses the current trailing window; portfolio turnover and
lagged exposure extend the net-return hull to [t-W,t]. The installed pandas3.0.6
Cython rolling-max kernel selects existing window operands without a floating
sum/variance accumulator. Global engine options can change dispatch, however;
mathematical locality and bounded controls do not authorize general rolling
support. Source review:
[pandas3.0.6 roll_max](https://github.com/pandas-dev/pandas/blob/v3.0.6/pandas/_libs/window/aggregations.pyx#L913-L1051).

No new measurement or kernel/engine support contract is adopted here. Stable
factory identity is an independently reviewable prerequisite, preserving the
existing registry behavior before a separate scientific decision.

## Decision

Introduce module-owned high_proximity_factory alongside the three existing
stable factories. Replace only xs_52w_high's outer anonymous factory with that
function. Its returned callable retains the exact original expression:
high_proximity_signal(prices,int(p["window"])). Parameter lookup and int
conversion still occur when the signal callable runs, not when it is built.
Keep the captured mapping by reference, including existing mutation and native
error behavior. Keep the shipped126/189/252 grid and every other registry entry.

Do not change signal arithmetic, rolling engine selection, allocation, search,
purged support/status/method rules, models, API, UI, thresholds or accounting-v14.
xs_52w_high remains explicitly unsupported for purged measurement. Any later
extension requires a separate ADR, engine/dependency-domain evidence, TDD and
honest persisted method attribution. No generated or frozen evidence is replayed.

## Alternatives

- Recognize anonymous factories by name/grid: cannot distinguish substituted
  callables and repeats ADR-325's rejected identity shortcut.
- Implement rolling support in the same change: combines a representation-only
  prerequisite with a new scientific evidence contract; defer that larger slice.
- Force a rolling engine now: would change existing signal execution semantics
  and is unnecessary for stable callable identity.

## Verification and reversal

Observe failing registry identity tests before source edits. Preserve original
signals/portfolio outputs, lazy parameter lookup/coercion, error timing and
mapping capture with deterministic controls. Existing purged support must still
refuse this family. Compare the whole prior registry AST except the new helper
and exact outer-factory replacement, preserve other backend/frontend/data bytes,
and verify search/gate fingerprints. Require independent research review, full
foreground make check-all and exact published master CI.

Reversal removes the helper and restores the original outer lambda. This changes
no measured scientific result in either direction. Rolling-max support remains
unadopted under both implementations.
