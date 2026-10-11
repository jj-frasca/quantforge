# FINDING-191: SIC driver reruns and replaces a published single look

- **Status:** Corrected
- **Date:** 2026-10-11
- **Severity:** High — repeated-look and evidence-publication boundary
- **Scope:** backend/scripts/sic_composition_test.py
- **Decision:** ADR-242

## Evidence

ADR-161 section 8 permits one look; its Result records completion and explicitly
prohibits a rerun without a newly pre-registered follow-up. The driver starts by
reading the experiment and fundamentals pools, computes run_test and writes
OUT unconditionally. The registered result already exists on master.

Two independent reproductions used only synthetic monkeypatches and temporary
destinations. With an existing result, input access and mocked inference both
executed, main returned zero and replaced the original bytes. This establishes
an operational route to another look on growing pools, not that the actual
published inference was rerun or corrupted. No actual cohort was recomputed
and no generated repository artifact was changed.

## Correction and verification

ADR-242 adds refusal before inputs when the output is occupied and exclusive
publication to preserve a late-arriving result. Before implementation, scratch
tests observed seven failures and one preserved run-gate case. All 37 affected
tests passed afterward in parent and independent review; independent late
directory and symlink probes also preserved competing destinations. The input
analysis AST and statistical module are unchanged. Published result bytes remain
identical to HEAD (SHA256
8e34dd15688bce72b5704b0e9ac791dbc18a2ba438d6e89e9040f567af996e8b).
Full foreground delivery verification is recorded in the session ledger.
This scope does not add a concurrency-wide analysis lock or guarantee atomic
completion after process failure, and it changes no statistical procedure.
