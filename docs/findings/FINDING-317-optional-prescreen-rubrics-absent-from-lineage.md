# FINDING-317: Optional pre-screen rubrics are absent from experiment lineage

- **Status:** Surviving-row rubric lineage corrected (ADR-375); full admission replay unmeasured
- **Date:** 2026-10-26, Codex autonomous session1 (ISO2026-W44)
- **Severity:** Medium for reproducibility of opt-in screened hunts
- **Affected:** run_universe_hunt, ValueGateConfig, QualityGateConfig, Experiment
- **Related:** ADR-023, ADR-029, ADR-137, ADR-147, ADR-372, ADR-373

## Evidence before ADR-375

ADR-023 describes a versioned screen recorded with the run. ValueGateConfig's
class docstring and quality_filter's module docstring repeated that claim.
Both configs compute deterministic version hashes, but run_universe_hunt uses
these policies only for admission. Neither the complete configs nor their hashes
are attached to surviving Experiment records. Experiment.gate_config and
manifest.validation_config_hash describe the separate technical GraduationGate.

A fresh mock-only witness runs the actual universe orchestration, dataset and
manifest enrichment, experiment validation and InMemoryExperimentStore. The
search function alone returns one fixed synthetic Experiment; no backtest,
provider network request or calibration executes. All cases share the same
three-row synthetic ResearchDataset, valuation score0.9 with margin_of_safety0.1,
quality_score0.9, F-score9, finalist, experiment identity and caller rationale:

| Case | Value rubric | Quality rubric |
|---|---|---|
| Off | None | None |
| Permissive | min_score0.2; keep_unscored=True; require_margin_of_safety=False | min_quality_score0.2; keep_unscored=True; min_f_score=None |
| Strict | min_score0.7; keep_unscored=False; require_margin_of_safety=True | min_quality_score0.7; keep_unscored=False; min_f_score8 |

All three pass admission. Their actual stored Experiment JSON is byte-identical
within the witness despite distinct enabled config hashes and off/on states.
The fresh parent payload SHA256 is
`e955de92d2109d3b8812054ae04b8d6de4df694f14623c5fba28b5ca5800f0c9`.
The earlier prospective witness reaches the same equality; report UUID creation
means hashes need not agree across separate executions. This demonstrates missing
policy information independently of any search outcome.

The stored undervaluation score does not identify whether it was screened or
under which rubric. Quality admission input and its screen result are not stored
on the surviving experiment. Filtered/error dictionaries are transient hunt-result
entries; they do not become Experiment rows. Caller rationale passes unchanged,
and the built-in drivers supply constant rationales without the policies.

CLI stdout does print enabled minima (value and quality in hunt.py; value in
run_hunt.py). Logs therefore supply partial external context. Exact executed code,
defaults and retained CLI logs may reconstruct ordinary CLI-only flags; do not
claim every historical run has no evidence. These lines do not record full configs
or hashes and cannot cover arbitrary programmatic policies. No actual affected
enabled production cohort, false graduate or trade is established. Screens remain
off by default; this finding does not change graduation arithmetic or thresholds.

Receipts: /tmp/qf-w43-s34-prescreen-lineage-review.{py,json,md} and fresh
/tmp/qf-w44-s1-prescreen-lineage-parent.{py,json}. The fresh script reads the
original synthetic valuation fixture without executing old receipt writers.

## Correction and remaining limits

The first correction (ab2fad54) fixed reporting claims while preserving behavior.
ADR-375 separately adopts nullable surviving-row admission_policy evidence after
research/data review. Its complete effective config snapshots distinguish enabled
rubrics and known inactive screens; absent historical/direct-search policy remains
unknown. Both config keys are required when a policy object is present, preventing
an empty object from silently asserting known off. Existing config version hashes
derive from those complete snapshots; technical gate lineage remains separate.

Canonical finite JSON must survive nested reconstruction unchanged before any
normalization. Ordinary constructors already normalize their supported inputs.
Malformed unchecked active copies/noncanonical raw evidence refuse at post-search
attachment instead of silently describing a different rubric. Inactive configs
remain ignored. Existing provider/config is-not-None guards and callback order
remain; ValueScreen can filter malformed copies before any snapshot is attached.
These refusals add no None fallback or complete attempted-trial history.

This repairs rubric lineage for new surviving universe rows only. No historical
config is inferred or generated file migrated. Full replay still needs requested
roster, source score availability/cutoff, quality admission input and filtered/error
outcomes; zero-survivor runs carry no Experiment policy. Retention removes evidence
with its row, and older writers can drop new fields when rewriting. A run-level
artifact remains a distinct future design, not a claim established here.

## Verification of the initial reporting correction

Fresh parent and independent reproductions each confirmed three identical
persisted payloads with distinct policies and zero actual searches. Final
research review approved all five changed paths. Parent and independent checks
matched all three whole Python module ASTs after excluding docstrings; schemas,
defaults, hashes, screen decisions and scientific expressions are unchanged.
No new behavior test is needed for this text-only correction.

Foreground make check-all passed 14,953 backend tests (97.42% coverage),
746 frontend tests (97.88% statements), lint, formatting and types.
Log: /tmp/qf-w44-s1-check317.log. No generated or frozen evidence was changed.

## ADR-375 verification

Before schema
changes all 38 new tests failed from the absent evidence boundary; no collection
error was counted as RED. The initial postpatch run passed 37 and exposed one
incorrect prospective assumption: unchecked keep_unscored='false' is coerced by
ValueScreen to filtered, so it does not reach post-search attachment. The corrected
refusal witness uses 'true'; a separate control retains the false-filtered path.
This changed test evidence, not runtime screening. Expanded 44 tests now pass,
including a Hypothesis exact finite-threshold/hash round-trip invariant.

Final research and data-engineering reviews approved all ten paths; each
independently repeated the 44 tests without live/integration selection. The
focused synthetic suite passed 155 tests. The 20 frozen ordinary controls match
except the new admission evidence and two expected manifest-error diagnostic
input representations containing that field; error types/reasons, decisions,
callbacks and store behavior match. Four whole-module AST comparisons allow only
the agreed schema/import/freeze/metadata additions and docstrings.

All 607 existing source files and 3300 records retain exact source hashes and old
canonical payload hashes after asserting and removing only the new top-level
admission_policy=None. Parent and independent replays pass; baseline receipt
SHA256 is c429198a84a77f155f88abb3f8294c9be01c8a2b8d3589a33644bc1787a9c194.
No generated rewrite or historical off-state inference occurred.

Fresh foreground make check-all passed 15,012 backend tests (97.43% coverage),
746 frontend tests (97.88% statements), lint, formatting and types. Logs:
/tmp/qf-w44-s1-admission-{red,green-final,focus}.log and
/tmp/qf-w44-s1-check375.log. Pool/preservation scripts and receipts:
/tmp/qf-w44-s1-admission-pool-audit.py,
/tmp/qf-w44-s1-admission-pool-before.json and
/tmp/qf-w44-s1-admission-preservation.py.
