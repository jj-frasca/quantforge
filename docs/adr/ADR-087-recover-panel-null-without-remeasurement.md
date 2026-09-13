# ADR-087: Recover a completed panel-null artifact without remeasurement

- **Status:** Accepted
- **Date:** 2026-09-13
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-023
- **Extends:** ADR-030, ADR-081

## Context

ADR-081 fixes one 400-panel look and forbids extending or repeating it after seeing the result.
Its workflow uploads 100 shard artifacts, consolidates them, uploads the final measurement, and
then pushes the generated file. GitHub Actions re-runs are new attempts of the same workflow run;
the platform preserves the dispatch SHA but does not make earlier-attempt artifact availability a
safe merge contract. A failed-job rerun can therefore lack successful shards from the prior attempt.
If only the final git push fails, recomputing all jobs is worse: the inference already exists in the
uploaded final artifact and logs, so another calculation is an unpriced look.

## Options considered

1. **Tell operators to re-run failed jobs.**
   - Pro: minimizes repeated compute.
   - Con: successful matrix artifacts from an earlier attempt are not guaranteed inputs to the new
     attempt, so consolidation can be incomplete.
2. **Always re-run all jobs.**
   - Pro: creates one complete, internally consistent artifact set under the original dispatch SHA.
   - Con: it needlessly repeats completed work and violates the one-look rule after consolidation
     has already exposed the inference.
3. **Publish the exact final artifact through a separate recovery mode.**
   - Pro: preserves the already completed result byte-for-byte and performs no new search or
     inference.
   - Con: adds a second manual path to the workflow and depends on the final artifact's retention
     window.

## Decision

Choose option 3 for post-consolidation failures. Add a mutually exclusive `recovery_run_id` input
to the existing manual workflow. In recovery mode, skip preparation, every batch, and consolidation;
download `panel-null-measurement-<recovery_run_id>` from that workflow run with read-only Actions
permission; validate the contained final artifact through the production Pydantic boundary; write
its canonical JSON to the ADR-030 path; and use the existing rebase/push retry discipline. Recovery
also requires the source bytes to equal that canonical serialization, so ignored unknown fields or
alternate encodings cannot be carried into the generated record outside the validated model.

For a failure before the final measurement artifact exists, recovery means **Re-run all jobs**, not
failed jobs or a single matrix job. The original dispatch SHA and inputs are retained, and no
complete inference existed to preserve. The final artifact remains retained for 30 days; extending
that window would consume more repository storage without improving ordinary execution.

## Consequences

- A push-only failure can be repaired without another observed statistic or another 400-panel run.
- Recovery remains inside the same manual, cloud sole-writer workflow; local sessions still never
  edit or commit `data/*.json`.
- The recovery command must reject malformed/incomplete artifacts before touching the destination.
- Operators must distinguish pre-consolidation failure (full rerun) from post-upload failure
  (publish-only recovery). A failed-job or single-job rerun is never a valid recovery procedure.
- The measurement remains unspent; this ADR adds no dispatch and changes no seed, statistic,
  inference input, validation threshold, or generated artifact.

## Reversal

Remove the recovery input/job and publishing validator. That restores FINDING-023 and is unsafe
after a completed artifact has ever required push recovery.
