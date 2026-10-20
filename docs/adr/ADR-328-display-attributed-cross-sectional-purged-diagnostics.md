# ADR-328: Display attributed family-local cross-sectional purged diagnostics

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 6, ISO 2026-W43
- **Extends:** ADR-322/325/327
- **Addresses in part:** FINDING-265

## Context

ADR-327 publishes exact reconstructed per-family purged evidence. The frontend currently strips the additive fields and says PCV results are unpublished in its panel. Readers cannot distinguish current unsupported recipes and empty retained-fold geometry from historical missing evidence, or see the paired controls already measured by supported families.

The browser has a separate representability boundary: Python permits arbitrarily large integer geometry, but JSON responses are parsed into JavaScript numbers. Even individually safe integer counts can produce unsafe intermediate arithmetic. Client validation must neither round geometry nor allocate arrays from requested bars or folds.

## Decision

Mirror the existing wire evidence in the cross-sectional Zod boundary and display one additional table column, “Purged CV mean Sharpe”. Preserve all existing metrics, IC, WF, server-issued graduation, loading/error/empty behavior and latest-record semantics. Never calculate new scientific scores, subtract a control to invent excess, infer historical attribution or recompute the verdict.

Accept nullable/optional trial purged_cv_oos_sharpe and purged_diagnostic for historical compatibility. Recognize the exact published method/status/reason/dependency-rule identities. Require finite scalar and paired means. Validate structural coherence only: measured inherited scalar equals its nested mean; unsupported and no_usable_folds scalars are null or absent; unsupported evidence has its reason and no support/score claims; supported evidence has complete support geometry and no reason; actual embargo equals max(original floor, allocated lag). Bars cover requested folds, measured evidence has positive retained geometry and both paired means, and no-fold evidence has empty retained geometry and no means.

Validate parsed counts with z.int(): positive bars/lag, at least two requested folds and nonnegative floor/embargo/ordinals. Reject unsafe JavaScript integer inputs through the existing request-error state. This explicitly declines backend-valid Python geometry outside the safe range; it does not coerce, truncate or accept rounded unsafe backend integer counts. Zod validates parsed JavaScript values, not original JSON tokens: malformed fractional tokens may already have rounded before schema validation. Exactness here concerns the published backend integer contract, without a new lossless parser or raw-token certification. Convert accepted counts to BigInt only inside geometry validation. Reproduce the backend prefix/suffix binary searches with exact integer arithmetic; validate kept cardinality and strictly increasing, unique, in-range membership. Do not generate requested-fold arrays or row arrays. Complexity remains O(log K + m) time and O(1) extra geometry space beyond the received ordinal sequence.

If any family has current evidence, every family must have current evidence with common method/search bars/requested folds/floor. Attributed WF search bars must agree. Family embargoes, retained identities and paired benchmark means may differ. Entirely absent nested evidence permits finite historical unpaired scalars and null scores. Reduced wire checks cannot certify original factories, source provenance or allocated parameter coverage; source reconstruction and the producer retain those responsibilities.

For measured rows show the reported mean and a clearly labeled same-retained-fold equal-weight universe benchmark mean within that family's cell. Zero and negative scores remain measurements. Use a native collapsible details element with summary “Fold evidence” for actual search bars, kept/requested folds, original floor, allocated price lag and actual embargo. If displaying fold identities, label them as human-facing one-based fold numbers. Keep identity lists inside the details; do not create an inline metadata wall. Do not expose raw method or dependency-rule identifiers in product copy.

Unsupported rows read “not measured” plus a plain-language reason: unsupported/custom recipe, unsupported parameters or unsupported price dtype. No-usable-fold rows read “not measured · no usable folds” and expose their supported geometry under “Fold evidence”. Historical finite scalars read “legacy, unpaired”; historical null/absent scores read “not measured”, without invented pairing or geometry.

Revise the existing caption to describe family-local retained-fold means and controls. Preserve the whole-sample family-winner, internal-configuration-cost/account-switching, benchmark-turnover and static-snapshot caveats. State that later training is intentional and support is restricted to audited direct-shift recipes. Means of fold Sharpes are not Sharpe of a stitched executable policy. Do not imply universal source isolation, statistical independence, new calibration or support for deferred rolling/static families.

Update the endpoint cold-memory frontend contract to describe publication and the representability policy. No evaluator, search, API production model, threshold, accounting, generated JSON record, frozen cohort or workflow change is included. Record the remaining unsupported-family scope in the written finding; panel publication alone does not close that methodology limitation.

## Alternatives and reversal

1. One family-local score/control column with collapsible evidence: chosen; keeps the table readable while preserving attribution.
2. A shared benchmark caption: rejected because retained-fold populations and controls can differ across families.
3. Inline all metadata: rejected because it overwhelms the data table.
4. Number-only geometry arithmetic: rejected because safe input counts can have unsafe intermediate sums/products.
5. Coerce enormous Python counts into numbers: rejected because it can alter geometry silently.
6. Reimplement scoring or graduation: rejected; the server remains authoritative.

Reverse only the new client fields/structural checks, new column and publication caption/documentation changes. Preserve backend API/source evidence, historical generated rows and written findings.

## Verification

Observe failing tests before runtime source edits for measured/unsupported/no-fold rendering and preservation, finite and scalar binding, branch completeness, recognized identities, count types/bounds, embargo agreement, complete exact ordinal geometry, all-family request agreement and attributed WF bars. Include duplicate/unsorted/out-of-range/missing/extra/wrong retained identities, null versus absent historical evidence, zero/negative scores and distinct family benchmark/geometry fixtures. Use direct Zod tests for nonfinite values that JSON cannot represent, and MSW tests to prove real boundary preservation and malformed evidence reaches the existing error state.

Cover MAX_SAFE_INTEGER accepted geometry with BigInt-only intermediate operations, overflow-sensitive end-plus-embargo cases, unsafe integer rejection including raw JSON oversized count tokens, and huge requested counts with a tiny received ordinal set that must finish without requested-count allocations. Never construct enormous expected lists. Bounded exhaustive geometry controls may compare the compact algorithm with direct small-fold enumeration in tests.

Render one column; assert native “Fold evidence” summaries and detail contents, human-readable reasons, explicit supported no-fold geometry, historical unpaired versus null states, absence of raw method/rule IDs, per-family controls and unchanged server verdict. Deliberately update the existing eight-header/unpublished-PCV test; retain the other old behavior coverage. Verify keyboard-accessible native disclosure behavior and readable table layout in browser QA once implementation is adopted.

Independent frontend and research plan review preceded adoption; final source review is required. Run targeted Vitest tests for types, service and panel after RED/GREEN, then TypeScript/build and required coverage/checks. Run foreground make check-all before the explicit-path commit; fresh fetch/rebase, rerun make check-all if upstream code arrived, push HEAD:master without force and watch the exact master CI run before continuing. Leave no verification running in the background.
