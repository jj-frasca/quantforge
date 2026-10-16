# ADR-294: Attribute displayed calibrations to the current default procedure

- **Status:** Accepted
- **Date:** 2026-10-16
- **Deciders:** Codex autonomous session 19, ISO 2026-W42
- **Resolves:** FINDING-248
- **Extends:** ADR-044/053/065
- **Relates to:** ADR-030/047/048/051/158/291

## Context

Every committed null and power search fingerprint differs from the current v14
full-catalog default, although the gate hashes match. Existing API endpoints
serve these valid historical artifacts beside live pool statistics without a
current-default comparison. The power caption also asserts the same history as
a real hunt, whose available history actually varies by symbol. This can attribute
historical measurements to a different deployed procedure without changing any
number. Stored historical arithmetic is not shown to be wrong.

## Decision

Add presentation-only `compatibility` metadata to each null-calibration row and
power sweep returned by the existing read-only list endpoints. Retain all
scientific fields, order, values, missing-directory empty-list semantics and
immutable artifact models; write no generated file. Compute one typed current
default reference per request through public `calibration_search_version`,
`GateConfig` and `CALIBRATION_N_BARS`, with explicit full-catalog canonical names,
n_per_param=3, refine=True/span=.25 and observed selection. No new search or
calibration is performed. Fingerprints describe procedure, not unrelated Git
changes; no runtime Git subprocess or deployment-revision claim is needed.

Attach metadata to the same parsed artifact object as its numbers. Compare
original recorded metadata before scientific-model defaults can supply absent
lineage. Return explicit search, gate and history dimension states plus reasons
and the captured reference. Each dimension is MATCHED, DIFFERENT or UNKNOWN;
overall DIFFERENT takes precedence over UNKNOWN, and MATCHED requires all three
matches. Missing/sentinel identity is unknown, never an inferred match. Any
known mismatch remains visible even when another dimension is unknown.

Require every null symbol's recorded history to match the exact target; complete
history has exactly n_symbols entries, each a positive integer equal to target. For power, compare the sweep
header and every cell's own identities and complete history against the same
reference; missing/empty cells cannot certify a sweep. A different recorded
history suffices for DIFFERENT even when its vector is incomplete. Do not use
pool history tolerance or medians to hide mixed/partial histories. Custom
procedures can intentionally differ and are not thereby invalid. The reference
is the current default calibration target, not a claim about every real symbol.

If computing the reference fails, preserve historical data with UNKNOWN context.
Keep malformed scientific artifact errors intact. Do not add persistent caching,
companion fetches, digest registries, migrations or a second scientific validator.
Existing null-comparison matching and minimum-observation guards remain intact.

Frontend schemas accept absent/null metadata from older servers and display
UNKNOWN. Show qualification adjacent to every row/sweep and preserve rates, N,
measured histories and caveats. Expose recorded/current search and gate identities
in adjacent details; power qualification covers all cells. Replace unsupported
same-hunt-history wording with the recorded bar count. Matching fingerprints and
history establish compatibility only, not market truth, power under other laws,
simultaneous bounds, gate authorization or scientific certification.

## Alternatives considered

1. Keep only stored hash prefixes: leaves current attribution unresolved.
2. Companion reference endpoint and client comparison: scientifically possible,
   but adds a query and duplicates nested/history comparison in the frontend.
3. Filter or relabel historical artifacts: loses evidence or violates single-writer
   ownership; preserve and qualify instead.
4. Recalibrate as a UI fix: changes measurements and does not prevent recurrence.
5. Hash whole Git revisions or add artifact digest joins: unnecessary when the
   API computes context on the same artifact read with one captured reference.

## Verification and reversal

Tests first for matched/different/unknown identities and complete/mixed/missing
history, nested cells, legacy sentinels, custom selector, unavailable reference,
unchanged values/order/files and old-server visible UNKNOWN. Preserve historical
comparison regressions. Require independent research/frontend review, foreground
make check-all and exact master CI. Remove the presentation DTO/metadata and UI
qualification to reverse; scientific evidence and research behavior are untouched.
