# FINDING-313: The development lock retains vulnerable virtualenv activation code

- **Status:** Corrected
- **Date:** 2026-10-25, Codex autonomous session34 (ISO2026-W43)
- **Severity:** High (upstream advisory; no local exploitation established)
- **Affected:** backend/uv.lock, virtualenv via the pre-commit development dependency
- **Related:** FINDING-086

## Evidence

GitHub reported open Dependabot alert 16 on master 02517916. The lock and installed
local environment both contain virtualenv 21.7.13. The existing security-floor
regression still allows that version, which addressed the earlier F086 advisory.

[GHSA-8rjx-v5ww-45pp / CVE-2026-113776](https://github.com/pypa/virtualenv/security/advisories/GHSA-8rjx-v5ww-45pp)
reports that sequential activation-template replacement can rewrite placeholder
names inside already-quoted values, permitting code execution when a crafted
path or prompt is activated. The affected range is 20.26.6 through 21.14.1;
21.14.2 is the first patched version. The upstream
[fix 602b2662](https://github.com/pypa/virtualenv/commit/602b26623a724827ff171bf11fef4ad186d01f74)
uses one substitution pass and adds a placeholder-containing path regression.

Existing [Dependabot PR 60](https://github.com/jj-frasca/quantforge/pull/60)
targets 21.14.13 and has green backend/frontend/hooks checks. Its lock update also
changes distlib and packaging; those changes require dependency-level review,
not automatic wholesale adoption. The official
[21.14.13 release](https://github.com/pypa/virtualenv/releases/tag/21.14.13)
includes additional shell-prompt security fixes (GHSA-cx6f-vjhg-g3cc) and
exclusive-create hardening. Target 21.14.13 rather than stopping at the older
first fix. No attacker-controlled activation, exploit or application compromise
has been observed in QuantForge. This is development-tool exposure, even though
the alert API labels the lock dependency scope as runtime.

## Correction

Follow F086's existing targeted security-lock update policy. Raise the virtualenv
regression floor to 21.14.13 first and observe failure against the original lock.
Resolve only the targeted virtualenv upgrade, allowing transitive changes only
when required by its declared dependencies. Preserve application constraints,
scientific stack, validation thresholds, generated records and workflow behavior.
Inspect package-level lock deltas, sync the environment, rerun the regression and
full foreground make check-all, then individually publish and verify exact CI.
Confirm the original alert closes through GitHub's authoritative API afterward.
No new architectural policy or dependency role is introduced.

## Verification

The existing lock-floor regression failed before the dependency update:
virtualenv 21.7.13 did not meet the new 21.14.13 floor. It passed afterward.
PyPI release metadata requires distlib>=0.4.3 and packaging>=26.3, justifying the
resolver's two transitive changes to 0.4.4 and 26.3. All other 80 package records
and top-level lock metadata match the original exactly; pyproject.toml is unchanged.
Receipt: /tmp/qf-w43-s34-security-lock-delta.json.

A no-seed/no-network local virtualenv with the upstream advisory's
placeholder-containing directory and embedded shell syntax activated in bash
without creating the command's marker; VIRTUAL_ENV preserved the resolved literal
path. The initial probe compared macOS /var against its /private/var target;
correcting that oracle to the resolved path passed. This bounded smoke check does
not certify every shell or exposure path. Receipt:
/tmp/qf-w43-s34-activation-smoke.json.

Fresh foreground make check-all passed all 14,831 backend tests (97.42% coverage),
746 frontend tests (97.88%) and lint/format/type checks with the updated environment.
Log: /tmp/qf-w43-s34-check-security.log. No application source, financial estimator,
validation threshold, generated record or workflow changed.
