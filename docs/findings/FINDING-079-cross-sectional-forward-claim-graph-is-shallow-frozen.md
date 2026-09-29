# FINDING-079: Cross-sectional forward claim graph is shallow-frozen

- **Severity:** High — a durable panel-forward claim can change under the same frozen factor identity
- **Status:** Resolved by ADR-149
- **Date:** 2026-09-29
- **Affects:** ADR-025, ADR-140, ADR-143, and ADR-144 cross-sectional forward records

## Finding

`CrossSectionalPosition` defensively freezes its reconstruction parameters, ordered universe, and
fundamental snapshots, but its lifecycle reasons, forward-equity curve, and ordered component
evidence remain mutable. Caller-owned or public in-place edits therefore change the next JSON
serialization without changing the factor, frozen universe, freeze time, or score timestamp.

Construction also accepts contradictory lifecycle and score claims: an open factor may carry
retirement metadata, a retired factor may omit its time or reasons, and score evidence need not
match the frozen universe's ordered symbols or one executed revision. Forward counts and statistics
may be invalid, while a non-empty curve need not match its declared bars, post-freeze chronology,
positive equity values, or terminal factor/benchmark returns. Production managed updates and the
JSON store both trust validation-bypassing `model_copy(update=...)` values.

No cross-sectional forward book is committed in `data/`, so this correction does not require or
authorize fabricating legacy records. Evidence-null scores and empty curves remain intentionally
supported for ADR-140 and ADR-025 compatibility.

## Required correction

At `CrossSectionalPosition`, validate lifecycle identity, finite/non-negative reconstruction cost,
unique ordered universe identity, score counts/statistics, ordered complete evidence identity, and
any non-empty curve's length/order/post-freeze/positive/terminal relationships. Defensively freeze
the complete nested score and lifecycle graph while preserving JSON object/array shapes. Managed
updates must reconstruct through validation and the JSON store must revalidate claims before
writing. Preserve nullable evidence and empty legacy curves. Do not change factor formulas,
lifecycle thresholds, benchmark definition, generated data, or historical claims.
