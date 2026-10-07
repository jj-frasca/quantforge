# FINDING-124: PBO coerces original return evidence

- **Date:** 2026-10-07
- **Severity:** Medium — a live statistical gate can reinterpret malformed evidence
- **Status:** Resolved — ADR-189

## Evidence

For the four-row return matrix [[.01,-.02],[-.02,.03],[.03,-.01],[.04,.02]], two-group PBO
returns 1.0. Adding imaginary component 1j to every entry still returns 1.0, with a warning that
imaginary values were discarded. Converting that matrix to numeric strings or object dtype also
returns 1.0. The corresponding boolean sign matrix returns 0.75. All are ordinary range-valid
results despite source evidence outside the real nonboolean numeric return-matrix contract.
ADR-106 checks converted shape/finiteness but coercion already discarded original source meaning.

## Correction and limits

ADR-189 preserves matrix-shape precedence, then requires original dtype kinds i/u/f before
float conversion. Five malformed-source dtype cases failed before correction, including timedelta
(which NumPy classifies under np.number). Numeric array/list representation oracles and existing
CSCV/noise/tie tests protect integer/floating matrices, constant columns and original statistics.
This is an evidence boundary, not a new PBO estimator, threshold or calibration procedure. Consumer review found only numeric production matrices; do not edit generated records.
