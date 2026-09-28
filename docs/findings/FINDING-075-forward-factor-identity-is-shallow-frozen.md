# FINDING-075: Cross-sectional forward factor identity is shallow-frozen

- **Severity:** High — a durable position can reconstruct a different factor under the same identity
- **Status:** Resolved by ADR-144
- **Date:** 2026-09-27
- **Affects:** ADR-025 cross-sectional forward positions

## Finding

`CrossSectionalPosition` is configured as a frozen Pydantic model, but its `parameters` dictionary
and `universe_symbols` list remain mutable. After construction, a caller can change the quantile or
strategy parameters and append, remove, or reorder universe members in place. `_factor_returns` and
panel evidence validation then consume the modified collections, so the same durable position
identity reconstructs and judges a different factor. Its next JSON serialization silently records
the altered claim.

The constructor currently makes ordinary Pydantic copies, so later mutation of caller-owned input
does not reproduce this defect; mutation through the public nested collections does. The risk is
therefore an exposed shallow-freeze boundary, not missing top-level assignment protection.

## Required correction

Make the forward position's reconstruction parameters and ordered universe actually immutable after
construction while preserving their existing JSON object/array shapes and round-trip behavior.
Do not change strategy formulas, defaults, lifecycle state, gates, or thresholds.

## Resolution

Position parameters are now defensively copied behind an immutable mapping proxy, and the ordered
universe is materialized as a tuple. Explicit parameter serialization plus Pydantic's tuple
serialization preserve the prior JSON shapes. Regression coverage proves caller and public nested
mutation cannot change the position and that JSON round trips reconstruct the same identity.
