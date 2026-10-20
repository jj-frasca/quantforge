# ADR-327: Publish attributed cross-sectional purged evidence in the API

- **Status:** Accepted
- **Date:** 2026-10-20
- **Deciders:** Codex autonomous session 6, ISO 2026-W43
- **Extends:** ADR-322/325
- **Addresses in part:** FINDING-265

## Context

ADR-325 measures restricted family-local purged diagnostics and persists explicit
unsupported/no-usable-fold outcomes. The reduced cross-sectional endpoint drops
this evidence, including the inherited scalar. API consumers cannot distinguish
unmeasured historical rows from a current unsupported recipe or empty geometry.
Independent research review recommends a bounded API slice before UI work.

## Decision

Add nullable purged_cv_oos_sharpe and purged_diagnostic to each existing trial
view. Project exactly from the reconstructed source experiment. Reuse the frozen,
always-revalidated PurgedDiagnostic model unchanged, preserving method/status,
reason, search bars, requested folds, floor, dependency rule, allocated lag,
actual embargo, kept ordinal identities and paired means. Never recompute scores,
assign historical methods, infer geometry or collapse statuses into a zero score.

Trial views require inherited scalar equality with measured nested mean; current
unsupported/no_usable_folds evidence requires the scalar absent. Entirely absent
nested evidence permits finite historical unpaired scalars. If any family has
current evidence, require all families to have it and share method/search bars/
requested folds/floor. Attributed walk-forward bars must agree. Family embargo,
kept folds and paired benchmark means may differ and must not be forced equal.

Reuse the allocation-free original-count and exact kept-set validators rather
than introducing another geometry implementation. Revalidate unchecked copies at
both public view levels. Keep full source reconstruction before projection: the
reduced trial view omits finalist parameters and cannot independently certify
supported factory/domain/allocated coverage. Wire checks establish structural
coherence, not scientific provenance or independent replay.

Preserve latest-record selection, missing/empty pool null semantics, all existing
metrics, WF/IC and server-issued graduation. Added fields default null. Frontend
Zod currently strips unknown fields, so the API addition is compatible; display
is deferred and the panel retains its accurate unpublished-in-this-panel caption.
FINDING-265 remains open for unsupported-family measurement and panel publication.

All ADR-325 scientific limits remain: only audited direct-shift/native Float64/
shipped domains are supported; later training is intentional; family means use
same retained-fold equal-weight controls with internal config costs, no added
benchmark turnover or account switching reconciliation. Whole-sample family
selection, rolling numerical history and static/PIT limitations are unchanged.
No evaluator, search, threshold, accounting-v14, workflow, generated record or
frozen-cohort change; no new calibration is authorized.

## Alternatives and reversal

1. Publish exact nested evidence with its inherited scalar: chosen, additive.
2. Publish one raw score only: loses attribution and current unmeasured reasons.
3. Use one experiment-wide benchmark: wrong when family embargos keep different folds.
4. Couple this with UI display: useful next slice, but requires independent client
   geometry/representability policy and frontend review.

Remove only the additive API fields/projection/validators to reverse. Preserve
backend measurements, historical generated rows and the written finding.

## Verification

Observe RED before runtime changes for exact latest measured/unsupported/no-fold
publication, distinct family pairings, zero/negative scores, legacy null/unpaired
records, missing/empty pools, direct wire contradictions and forged source/nested
copies. Exercise original count validity, unknown identities, finite scores,
scalar binding, complete common request and WF-bar coherence. Huge valid geometry
must validate without arrays. Preserve the25 frozen old API payloads exactly after
removing only the two additive trial fields, and retain research core/data hashes.
Independent review and fresh foreground make check-all precede explicit commit,
fresh fetch/rebase, immediate individual HEAD:master push and exact CI checks.
