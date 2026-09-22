# FINDING-032: Panel-null recovery is not publication-idempotent

- **Severity:** High — publish-only recovery can replace a different durable one-look record and
  treats an already-published identical record as a new generated-data commit attempt
- **Found:** 2026-09-22 by Codex hostile review of ADR-087 exact-byte recovery
- **Status:** Resolved by ADR-100
- **Affected:** `recover_panel_null.py`, `.github/workflows/panel-null-calibration.yml` recovery mode

## Finding

ADR-087 requires post-consolidation recovery to publish the completed artifact's exact bytes without
another measurement. The recovery command validates those source bytes and their producing workflow
identity, then unconditionally replaces the generated destination. The workflow unconditionally
stages and commits that replacement.

That is not an idempotent publication boundary. If the checked-out destination already contains a
different measurement, recovery overwrites it locally before git is asked to reconcile history. A
later rebase conflict is not a scientific invariant and cannot authorize replacing a different
durable one-look record. If the destination already contains the identical bytes, recovery still
attempts a second generated commit instead of reporting that publication is complete.

The measurement is currently unspent, so no generated artifact has been affected.

## Required correction

After validating the recovered source and authoritative run identity, inspect any existing
destination before mutation. Identical bytes must return successfully without rewriting the file;
different bytes must fail before destination mutation. The workflow must skip commit and push when
the validated recovery produced no staged change. Preserve every artifact byte, panel, seed,
statistic, inference rule, and validation threshold.

## Resolution

Resolved by ADR-100. Recovery now treats identical publication as a clean no-op, rejects a different
published measurement before mutation, and the workflow exits without a generated commit when no
recovery diff exists.
