# FINDING-165: Legacy null arrays accept invalid evidence

- **Date:** 2026-10-08
- **Severity:** High — durable diagnostic evidence validity
- **Status:** Resolved by ADR-216
- **Reproduced revision:** `f888f8f7`

Without symbol diagnostics, `NullCalibration` accepts legacy diagnostic arrays
containing infinity/NaN, holdout years zero, and a boolean bar count coerced to
one. Infinite walk-forward diagnostic evidence also survives merge reconstruction.
Raw percentile and matched-history consumers trust these arrays. ADR-213 guards
canonical leaves; ADR-215 guards root scalar claims; neither guards legacy
array elements.

These are constructed malformed inputs, not observed corruption of committed
artifacts or an incorrect published verdict. A bounded correction must validate
each present score as an original finite real nonboolean number, each present
bar count as an original positive nonboolean integer, and each present holdout
length as finite and positive. Do not clamp/drop elements or invent defaults.

Empty optional arrays remain explicitly unmeasured, and partial legacy arrays
retain their raw diagnostic use while remaining unpairable for excess. Preserve
valid signed/zero scores and numeric scalars. No new length/projection contract,
denominator, threshold, formula, identity or generated-data change is proposed.
Maximum/bar recomputation and other derived arithmetic remain separate boundaries.

## Correction and verification

ADR-216 validates original present elements before container coercion, sharing
the canonical leaf contracts. Against committed `f888f8f7`, the inherited suite
reproduced 49 failing rejection cases and 19 passing compatibility cases before
delivery. The corrected suite protects JSON loading, unchecked-copy merge,
signed/zero scores, numpy history, Fraction years, tuple containers, and empty
or partial legacy arrays. Independent review passed 226 focused tests and
validated all eight committed null artifacts (8,800 present array elements),
with unchanged JSON round-trips and seven extra adversarial numeric probes.
No array length, statistic, threshold, fingerprint,
or generated record changes. Full gate and read-only artifact compatibility
are required before delivery; downstream percentile arithmetic remains separate.
