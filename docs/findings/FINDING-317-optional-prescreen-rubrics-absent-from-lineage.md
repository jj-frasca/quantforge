# FINDING-317: Optional pre-screen rubrics are absent from experiment lineage

- **Status:** Open; reporting claims corrected, persistence design deferred
- **Date:** 2026-10-26, Codex autonomous session1 (ISO2026-W44)
- **Severity:** Medium for reproducibility of opt-in screened hunts
- **Affected:** run_universe_hunt, ValueGateConfig, QualityGateConfig, Experiment
- **Related:** ADR-023, ADR-029, ADR-137, ADR-147, ADR-372, ADR-373

## Evidence

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

## Bounded correction and open work

Correct the two reporting docstrings and cold memory to state the existing
persistence limit. This documentation correction does not resolve the missing
lineage. Keep accepted ADRs unchanged as historical decisions; no schema or
scientific behavior change is adopted here.

A later ADR must choose per-experiment snapshots or a run-level admission
artifact, with enabled/disabled/unknown states, compatibility and retention
specified before implementation. Historical absence must remain unknown rather
than being inferred as off. Configs/hashes alone would improve rubric lineage
but cannot reconstruct the screened universe: full replay also needs requested
roster, source score availability/cutoff, and filtered/error outcomes. No missing
historical evidence should be invented.

## Verification

Fresh parent and independent reproductions each confirmed three identical
persisted payloads with distinct policies and zero actual searches. Final
research review approved all five changed paths. Parent and independent checks
matched all three whole Python module ASTs after excluding docstrings; schemas,
defaults, hashes, screen decisions and scientific expressions are unchanged.
No new behavior test is needed for this text-only correction.

Foreground make check-all passed 14,953 backend tests (97.42% coverage),
746 frontend tests (97.88% statements), lint, formatting and types.
Log: /tmp/qf-w44-s1-check317.log. No generated or frozen evidence was changed.
