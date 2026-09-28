# FINDING-074: Fundamental score snapshots are shallow-frozen and admit non-finite values

- **Severity:** High — persisted factor identity can mutate or fail to round-trip
- **Status:** Resolved by ADR-143
- **Date:** 2026-09-27
- **Affects:** ADR-142 cross-sectional experiment and forward-position snapshots

## Finding

ADR-142 stores value and quality snapshots inside Pydantic models configured as frozen, but a
frozen model does not freeze nested dictionaries. Callers can mutate `experiment.value_scores` or
`position.quality_scores` in place after construction, changing the factor reconstructed from the
same durable experiment or position identity.

The same fields accept `NaN` and infinity. Pydantic serializes a stored `NaN` as JSON `null`, so the
model's own JSON output cannot reconstruct the original `dict[str, float]`; non-finite scores can
also change rank missingness without an explicit evidence failure. Direct construction additionally
accepts keys outside the frozen universe or in an order that does not match panel order, bypassing
ADR-142's producer-side projection contract.

## Required correction

Make both experiment and position construction revalidate score snapshots as finite ordered
subsets of the frozen universe, defensively copy them, and expose an actually immutable mapping.
JSON must retain the existing object shape and round-trip exactly. Keep `None` for legacy/unsupplied
families and preserve deliberate missingness through absent keys; do not coerce invalid values.

## Resolution

`FrozenScoreSnapshot` now defensively copies and blocks mutation. Shared model-boundary validation
rejects non-finite values and score keys that do not follow the frozen universe, and explicit field
serialization preserves the ADR-142 JSON object contract. Focused tests cover experiment and
position mutation, hostile values and keys, and exact JSON round trips.
