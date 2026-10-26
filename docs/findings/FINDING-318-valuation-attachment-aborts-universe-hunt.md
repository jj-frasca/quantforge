# FINDING-318: Valuation attachment escapes the per-symbol hunt handler

- **Status:** Corrected (ADR-374)
- **Date:** 2026-10-26, Codex autonomous session1 (ISO2026-W44)
- **Severity:** Medium for opt-in valuation hunt availability and result completeness
- **Affected:** run_universe_hunt valuation attachment
- **Related:** ADR-023, ADR-137, ADR-147, ADR-373

## Evidence

Experiment correctly refuses a valuation score whose symbol differs from its
own. Universe orchestration reconstructs the attached score outside its
per-symbol try/except, however. This raises out of the whole hunt, skipping later
symbols and preventing the structured UniverseHuntResult from returning. Earlier
valid rows may already be present in the supplied store. The invalid row itself
is not persisted; the identity validator works.

Parent and independent mock-only probes use actual validated synthetic scores,
ResearchDataset, Experiment/manifest enrichment and InMemoryExperimentStore,
with only run_search replaced by a fixed valid per-symbol result. A finite
valuation score0.9/MoS0.5 has symbol WRONG for requested BAD. For [BAD,GOOD2],
ValidationError escapes and GOOD2 is never visited. For [GOOD1,BAD,GOOD2], GOOD1
is already stored before the same exception escapes; GOOD2 is never visited.
Both record-only (value_config=None) and enabled-screen modes behave this way.

Matched controls instead supply correctly labeled valuation and a quality-report
symbol mismatch. Manifest reconstruction rejects BAD inside the existing try,
records errors['BAD'] and continues to GOOD2. Eight cases distinguish fault
placement from optional-screen configuration. No real search, vendor request,
cohort, generated record or trade was performed. No actual production corruption,
cohort loss or false graduate is established. A default hunt without a valuation
provider cannot trigger this witness.

Receipts: /tmp/qf-w44-s1-enrichment-review.{py,json,md} and
/tmp/qf-w44-s1-enrichment-parent.json.

## Correction and limits

ADR-374 moves only the existing optional valuation attachment/revalidation block
to the end of the existing per-symbol try. Retain the validator, exception classes,
error formatting, None behavior, screen order and later store/add boundary.
The bad score becomes a per-symbol error, never an unscored fallback, filtered
name or persisted invalid row. Search for BAD has already occurred; this does
not turn it into an unattempted admission or reconstruct missing trial history.

ADR-147 mandates identity refusal, not whole-hunt abort. ADR-373's provider
constructor refusals remain per-symbol errors; its separate fundamental-sweep
shard refusal remains unchanged. Store failures still propagate, and no atomic
whole-hunt store guarantee is introduced. Do not add an earlier symbol guard:
it would alter acquisition/search order and pre-screened mismatched-score behavior.
F317's optional rubric lineage gap remains independently open.

## Verification

Twenty deterministic ordinary controls are frozen before the patch: complete
experiment/result payloads, errors/filtered entries, stored rows and call order
for absent/None/unscorable/low/high scores, provider/manifest errors and store
ValueError/OSError propagation, each with screening off/on. Parent and independent
prepatch and postpatch replay match exactly. Baseline:
/tmp/qf-w44-s1-enrichment-baseline.{py,json}.

Before the source patch, the new tests observed four actual failures from the
escaping ValidationError and eleven passing controls. After relocation all
fifteen pass. The focused synthetic suite passed 133 tests with one live test
deselected; final independent research review approved all five paths and ran
113 synthetic tests with one live test deselected. Both whole-module AST checks
match after performing only the agreed block relocation. Existing direct
Experiment identity refusals remain unchanged and pass.

The independent reviewer initially omitted the marker filter in one broader
command, selected a free SEC live test and attempted ticker-map retrieval; that
run failed and is not counted as green or offline evidence. The corrected run
and all parent verification explicitly exclude live/integration tests.

Fresh foreground make check-all passed 14,968 backend tests (97.42% coverage),
746 frontend tests (97.88% statements), lint, formatting and types. Logs:
/tmp/qf-w44-s1-enrichment-{red,green,focus}.log and
/tmp/qf-w44-s1-check374.log. No threshold, schema, default, v14 identity,
generated record or frozen cohort changed.
