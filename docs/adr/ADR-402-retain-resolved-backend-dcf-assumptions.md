# ADR-402: Retain resolved backend DCF assumptions

- **Status:** Accepted
- **Date:** 2026-10-29
- **Deciders:** Codex autonomous session16, ISO2026-W44
- **Partially addresses:** FINDING-325's known assumption-persistence gap
- **Extends:** ADR-022/023/147/375/382

## Context and Options

IntrinsicValueResult retains resolved default/custom settings, but the composite
valuation drops them. Different caps can produce identical complete valuation
JSON. Independent research/data reviews approve a bounded backend snapshot.

1. **Reuse DcfAssumptions with local canonical reconstruction (chosen).** Avoids
   duplicate financial rules while retaining complete settings; malformed unchecked
   metadata can reduce availability after computation and settings repeat per row.
2. **Dedicated strict snapshot model.** Explicit required fields, but duplicates
   policy and strict float fields alone still silently convert integers.
3. **Store entire intrinsic result, extend records/API/UI now.** More disclosure,
   but broadens several independent schemas and remaining input/code attribution.
4. **Infer default settings from old values.** Small but invents historical evidence;
   different settings can yield the same output. Rejected.

## Decision

Add UndervaluationScore.dcf_assumptions: DcfAssumptions | None, default None and
omitted when None in Python/JSON serialization. Legacy missing/explicit-null and
direct absent settings remain unknown. Do not infer defaults for those cases.

A local before-field validator reconstructs a supplied model's complete
round-trip Python dump (or supplied raw input) through DcfAssumptions. Require
sorted compact JSON with allow_nan=False to match the reconstructed full dump
exactly, following ADR-375. Return the new frozen scalar model. No lossy JSON
mode, custom encoder, default=str or recovery is allowed. Partial raw mappings,
ignored extras and unchecked scalar coercions/default insertion refuse. Evidence
preservation concerns the round-trip dump, not hidden attributes or arbitrary
custom scalar protocols. The shared DcfAssumptions schema/config/defaults and
existing finite bounds, nonpositive horizons and economic validation stay.

At score_valuation's final constructor attach intrinsic.assumptions, the actual
resolved model, after existing calculations. Include default and unsuccessful
DCF results without implying every setting affected arithmetic. Do not store
the caller's unresolved None, rerun DCF, change numerical expressions or reorder
earlier refusals. Newly consumed malformed unchecked metadata may refuse after
computation, even when old DCF shortcuts skipped it; do not promise final error
ordering or fallback to unknown/default settings.

## Consequences and Verification

Existing complete Experiment/store reconstruction retains this declared nested
field with the valuation. Legacy JSON remains exact outside normal existing
model canonicalization; old writers and projected APIs/UI may discard metadata.
FundamentalRecord and end-to-end disclosure remain separate. Settings alone
do not certify score/config binding, input cash flows, price, periods/PIT,
producing code or numerical correctness. No historic reconstruction, generated
rewrite, threshold, fingerprint, v14 or frozen cohort change occurs.

Before source changes freeze default/custom/failed producer claims, exact legacy
valuation JSON, current generated pool rows/raw hashes, schemas and AST. Observe
RED retention, detachment, revalidation, canonical coercion/missing/extra refusal,
legacy omission, actual provider and Experiment/all-store roundtrip tests. Use
Hypothesis for finite settings roundtrips. Preserve numerical claims outside
the new field and exact AST outside declared additions. Obtain final independent
reviews, foreground make check-all and exact CI after individual safe publication.

Reversal stops new attachment while retaining nullable readers. Removing readers
can discard evidence and needs an explicit decision; preserve historical records.
