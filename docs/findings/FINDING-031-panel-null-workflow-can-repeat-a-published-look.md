# FINDING-031: The panel-null workflow can repeat an already published look

- **Severity:** High — a normal-mode rerun can recompute and expose a second fixed-tail inference
  after the first measurement has already been published
- **Found:** 2026-09-22 by Codex hostile review of ADR-087 one-look enforcement
- **Status:** Resolved by ADR-099
- **Affected:** `.github/workflows/panel-null-calibration.yml` normal-mode reruns

## Finding

ADR-087 says that a failure before consolidation requires a full rerun, while a failure after the
final artifact exists must use publish-only recovery. The workflow documents this rule but does not
enforce it. A GitHub rerun checks out the original dispatch SHA, which necessarily predates the
generated result commit. The generated destination is therefore absent in that checkout even when
current `master` already contains the completed measurement.

Such a rerun can prepare, execute 400 panels, consolidate, print, and upload a second inference.
A later rebase or push conflict against the existing generated file is too late: the prohibited
second look has already been observed.

## Required correction

Before any normal-mode preparation, fetch current `origin/master` and fail if the canonical
generated measurement path already exists there. Recovery mode must remain available because it
publishes validated bytes without remeasurement. Any future authorized new look must pre-register a
new identity and destination rather than bypass this guard.

## Resolution

Resolved by ADR-099. The input-validation job now checks authoritative current master and refuses a
normal run once the fixed generated destination exists, before preparation or search can start.
