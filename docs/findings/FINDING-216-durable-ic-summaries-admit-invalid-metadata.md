# FINDING-216: Durable IC summaries admit invalid and contradictory metadata

- **Status:** Corrected
- **Date:** 2026-10-12
- **Review:** Codex autonomous research review, ISO 2026-W42 session 3
- **Decision:** ADR-267

## Written finding and mechanism

ICSummary is frozen but has no finite/domain/identity constraints. Direct claims
and unchecked copies accept NaN mean, negative std, hit_rate=2, n_periods=-1 and
IR=99 with t=0. Scratch full trial/experiment/store reconstruction and reload retain
these invalid scalar claims; JSON can contain literal NaN, while standalone model
JSON normalizes NaN to null and then cannot reload it. Existing writer reconstruction
is sufficient once the missing leaf invariants exist; no writer redesign is needed.

These are screening diagnostics, not inferential t claims. Nonetheless, their
claimed formulas and basic scalar meanings must be truthful. This review does not
redraw null cohorts, change a selection/gate threshold, infer historical contamination
or rewrite generated records. Read-only census: 23 experiments, 242 IC dictionaries,
all finite/current domains and exact original IR/t coherence (zero residual).

## Narrow correction and limitations

Add finite fields, std>=0, hit_rate in [0,1], native Integral count>=2 excluding bool,
instance revalidation and exact original IR/t coherence with the unchanged std floor.
Retain coherent historical finite means slightly beyond an endpoint; leaf mean bounds
are explicitly deferred rather than inventing a tolerance or normalizing history.
Impossible-but-coherent finite mean metadata remains a documented limitation, while
ADR-266 protects actual original summary observations. No universal domain claim.

Independent pre-code review approved all 242 stored summaries exactly, legacy endpoint
roundoff, all 16 generators/45 configurations, native integer compatibility and
nested/store prewrite rejection using temporary files only.

## Observed verification

Before implementation: 90 genuine failures and 12 preserved cases. The affected
cross-sectional/endpoint suite passed 736 tests; after test-only import/dictionary
style cleanup, 107 leaf/endpoint tests passed again. Four serialization warnings
come from deliberately unchecked native adversarial payloads, not valid records.

Independent final review approved 180 leaf/domain/IC/endpoint tests, all 242
committed summaries constructed and JSON-roundtripped exactly, all 16 generators/
45 configurations with original exact summaries, five std-floor baselines, native
integer normalization, huge-count refusal, legacy endpoint/absent compatibility,
Hypothesis observations, nested prewrite byte preservation and no parent creation.
Production AST outside leaf/imports restores exactly to ADR-266. The synthetic
endpoint fixture now uses the unchanged producer formula instead of an inconsistent
t-statistic, retaining all endpoint/null assertions. No tests removed or skipped.

Session 4 independently repeated the final review: 180 targeted tests passed; all
23 committed experiments and 242 summaries load and roundtrip exactly. Complete
rank-IC series and summary dictionaries match the published baseline for all 16
generators/45 configurations, with five additional floor/signed baselines. Native
integer widths, invalid count encodings, nested prewrite preservation and production
AST outside the leaf were independently checked again.

Fresh session-4 `make check-all PYTEST_WORKERS=4` passed in the foreground:
5,540 backend tests and 363 frontend tests, with all lint/type/format checks green.
Frontend statement coverage is 97.63%; the backend gate exceeds its unchanged 85%
minimum. Exact master CI is checked after delivery.
