# FINDING-198: Paper promotion discards unvalidated source evidence

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — invalid graduation evidence can become a paper position
- **Scope:** freeze_graduate source-to-paper projection
- **Decision:** ADR-249
- **Prior art:** ADR-147/FINDING-077 and ADR-148/FINDING-078

## Evidence

A valid synthetic CRM experiment selects RSI window 14. An unchecked Graduate
copy changed to window 999 inside an unchecked Experiment copy is refused by
Experiment.model_validate, but freeze_graduate promotes a valid paper position
with window 999. A consistently copied failed gate (passed=False, dsr_ok=False)
in the graduate and best gate likewise violates the source graduation contract,
yet freeze_graduate promotes it. Independent synthetic reproduction confirms
both paths. The projection drops selected-trial/gate evidence, so PaperPosition
validation cannot discover the invalid source relationships.

Ordinary JSON stores validate source experiments. These are public unchecked-copy
reproductions, not observed bad portfolio records, broker execution or a measured
false graduate. No broker, credentials, real search, cohort or generated artifact
was accessed or rerun.

## Correction and verification

ADR-249 reconstructs the complete authoritative Experiment before projection,
without adding graduation or paper criteria. A single entry line re-enters source
validation before the original absent-graduate, deflation and output body.

Before code, nine invalid-source regressions failed and five preservation cases
passed. All 62 affected tests pass, including selection/strategy/parameter/gate
contradictions, fundamental/distress vetoes and refusal before deflation/output.
Independent review approved 72 exact published-baseline complete paper-position
JSON comparisons across modern/legacy selection, structured/absent holdout,
failing/passing/unknown universe verdicts and benign copies. Caller source JSON
remains unchanged; removing only entry reconstruction restores the published
whole-module AST.

Session 35 repeated independent review: 39 paper tests and 72 exact complete
position comparisons pass. The fresh full foreground delivery gate passes
4,987 backend and 363 frontend tests, with 97.75% backend and 97.63% frontend
statement coverage; lint and strict typing pass.
Universe-deflation failure remains recorded and paper eligible under ADR-033;
its threshold is unchanged. No broker actions or generated record changes.
