# ADR-083: Pin the panel-null executed code revision

- **Status:** Accepted
- **Date:** 2026-09-11
- **Deciders:** Codex adversarial validator under `.claude/CODEX_CHARTER.md`
- **Acts on:** FINDING-019
- **Extends:** ADR-081

## Context

ADR-081 freezes the statistical and source identity of the replicated correlated-panel null, but
not the complete code revision that executes it. GitHub Actions jobs run the workflow-dispatch SHA.
The sole-writer commit later rebases onto current master, so commit ancestry cannot recover which
tree generated the measurement. Configuration fingerprints do not cover implementation-only changes
to backtesting, validation, generation, or inference.

## Options considered

1. **Infer the revision from the generated commit's parent.** Simple, but wrong after the workflow's
   required `git pull --rebase` moves the artifact commit onto a newer master.
2. **Expand every existing fingerprint to hash all implementation files.** More granular in theory,
   but brittle: a transitive dependency can be omitted and independently maintained hashes can
   disagree about which code belongs to the procedure.
3. **Persist and verify the workflow dispatch git SHA.** One standard immutable tree identity covers
   the complete executable repository and survives generated-commit rebasing, at the cost of making
   otherwise identical runs on two commits distinct.

## Decision

Choose option 3. `PanelNullCohort` requires a 40-character lowercase hexadecimal `code_revision`.
The preparation command requires it explicitly and the workflow supplies `${{ github.sha }}`. Every
production batch also receives the current job's `${{ github.sha }}` and refuses a mismatch with the
manifest before constructing or invoking the search. Shards and the final calibration inherit the
field through the existing exact cohort identity. Local tests use explicit synthetic revisions.

## Consequences

- A committed measurement states exactly which repository tree produced all 400 replicates.
- A workflow whose frozen input pair and batch checkout identities diverge fails before expensive
  search execution.
- Re-running from a different commit is a different artifact identity even when policy fingerprints
  are unchanged; this conservatism is intentional for scientific provenance.
- No gate, validation threshold, selection rule, generated data, or existing measurement changes.

## Reversal

Remove `code_revision` and its preparation/batch checks. That restores FINDING-019's ambiguity and
must not be done after a measurement has been interpreted.
