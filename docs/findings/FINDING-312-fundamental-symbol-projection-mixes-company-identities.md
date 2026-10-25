# FINDING-312: Fundamental symbol projection can mix company identities

- **Status:** Corrected (ADR-371)
- **Date:** 2026-10-25, Codex autonomous session32 (ISO2026-W43)
- **Severity:** High for ambiguous symbol-based research inputs
- **Affected:** score_maps, make_quality_provider, cross-sectional driver input projection
- **Related:** ADR-029/142/143/155

## Current stored evidence

The newly arrived a292a17e weekly sweep leaves4258 canonically valid records
with unique CIKs. Input SHA256 is
92c4d4ea27b09958287c58b9183a025f856f251c1d8a017e5efa2e0e34a49cf6,
unchanged through parent/independent read-only audits. ADR-029 intentionally
merges by CIK; row validation cannot resolve symbol ownership across companies.

CIK1826011 changes symbol from PARAW to PARA (FY2025, quality0.4260077050041713,
value1.0). Retained CIK813828 also has PARA (FY2024, quality0.46459089205289994,
value0.8949779547367184). score_maps chooses the latter through dictionary
input order; reversing just these two records changes both scores and a
synthetic registry factor signal. The quality provider instead chooses the
former through its largest-year policy. Neither order nor fiscal year proves
which company owns a current traded symbol. Current default universes inspected
do not include PARA; no default-panel outcome, source-provider error, affected
trade, false graduate or historical incidence beyond this stored ambiguity is
established. No source fetch or real search was performed.

A separate canonical synthetic witness is stronger than choosing the wrong row:
one CIK supplies quality0.9/valueNone and another CIK supplies qualityNone/value0.2
under the same symbol. score_maps independently fills both legs, and the registry
can multiply them to0.18 although both source combined_score fields are None.
That is an unsupported cross-company composite, not merely a newer/older choice.

Independent receipts and scope review:
`/tmp/quantforge-session32-fundamentals-identity-receipt.json`,
`/tmp/qf-w43-s32-fundamental-projection-review.{md,json}`, and
`/tmp/qf-w43-s32-adr371-data-review.md`.

## Correction and limits

ADR-371 records the prospective policy before TDD/source changes: reject a symbol
owned by more than one distinct CIK at symbol-based projection. Detect ambiguity
before dropping missing legs, including case aliases under the quality provider's
existing uppercase lookup convention. Preserve original output-map keys and
same-CIK selection semantics. The quality provider refuses lazily when requested;
it must not turn ambiguity into None that keep_unscored could admit.

The cross-sectional driver projects only its resolved requested symbols before
score_maps, so an unrelated ambiguous symbol does not block a healthy panel.
Preserve globally supplied quality/value leg presence independently of requested
coverage: an existing supplied leg with zero requested scores remains an empty
mapping, not None, retaining its factor family and snapshot semantics. Resolve
ambiguity on the requested universe before price/frame acquisition and search,
not only on eventual fetched survivors. Single-name value-provider ordering
remains earlier than quality screening; no promise is made to prevent that call.

Do not repair generated JSON, select a CIK by fiscal year/score, change company
ranking or CIK merge policy, infer current ticker identity, rewrite frozen maps,
or alter thresholds/calibration. Historical snapshots lack owner metadata and
cannot be retroactively certified. Row validity and raw-source truth remain
separate from this source-projection guard.

## Verification

The interrupted session observed18 failing tests and58 passing controls before
implementation. The final identity suite has21 passing cases, including the
Hypothesis cross-company composite property; the expanded focused suite passed88.
Session34 independently repeated the21 identity tests and received research and
data final-review approval for all eight paths.

A fresh replay exactly preserved64 ordinary map/provider/screen payloads and
input JSON, all4258 canonical source records and their unchanged SHA256 above,
the default503-symbol projected snapshots, eligible registry families/grids and
three fundamental signal frames. Strict whole-module AST comparison admitted
only the explicitly adopted guard/provider/driver changes across three runtime
modules. These bounded controls do not certify arbitrary inputs or source truth.

Fresh foreground make check-all passed14831 backend tests (97.42% coverage),
746 frontend tests (97.88%) and all lint/format/type gates. The first auto-worker
run stopped on an unchanged Alpha4 property's200ms Hypothesis deadline
(336.96ms); the complete four-worker rerun passed with that deadline and every
assertion unchanged. No test was skipped or validation threshold weakened.
Local receipts: /tmp/qf-w43-s34-check371-four.log and
/tmp/qf-w43-s34-fundamental-independent-replay.json. No generated data changed.
