# FINDING-314: Refreshed dependency inventory exposes six additional advisories

- **Status:** Corrected
- **Date:** 2026-10-25, Codex autonomous session34 (ISO2026-W43)
- **Severity:** Critical (highest upstream advisory; no local exploitation established)
- **Affected:** backend/uv.lock and frontend/package-lock.json
- **Related:** FINDING-086, FINDING-313

## Evidence

After F313's virtualenv update passed exact CI, GitHub marked alert 16 fixed.
The refreshed inventory then exposed six open alerts across four other locked
packages. The initial one-alert response was not a complete enduring inventory.

| Package | Locked | First patched | Alerts | Severity |
|---|---|---|---|---|
| certifi | 2026.5.20 | 2026.10.19 | 17 | Critical |
| filelock | 3.29.0 | 4.2.1 | 18, 19, 20 | High / Low / Low |
| zod | 4.6.5 | 4.6.6 | 21 | High |
| undici | 7.30.0 | 7.30.1 | 24 | High |

The [certifi advisory](https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2)
reports compromised intermediate CA keys chaining to a bundled emSign root.
An on-path attacker with such a key could impersonate TLS endpoints. The fixed
bundle removes the affected trust; 2026.10.19 restores unrelated emSign roots.
Certifi participates in Python HTTP dependencies, so development-only assumptions
do not bound this package's exposure.

The filelock advisories cover [SQLite-backed read/write lock redirection](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8),
[Windows soft-lock timeout blocking](https://github.com/tox-dev/filelock/security/advisories/GHSA-567q-5qvw-pf92)
and [Windows SQLite side files](https://github.com/tox-dev/filelock/security/advisories/GHSA-9vhv-jxww-xfm5).
Affected operations depend on local shared-directory and platform conditions;
QuantForge has no established exploit instance. Updating to 4.2.1 is compatible
with virtualenv's declared filelock<5 requirement, subject to full verification.

The [Zod advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5)
reports memory exhaustion from excessive collection-validation issues. Zod is
QuantForge's frontend response boundary, so its parser behavior must remain
compatible with existing scientific-evidence readers. Target the existing
Dependabot PR 61's 4.6.7 patch within the declared 4.x range.

The [undici advisory](https://github.com/nodejs/undici/security/advisories/GHSA-xjj6-f33q-929c)
reports a process crash on excessive content encodings plus an early response
close. The fixed 7.x release is 7.30.1. The inspected dependency path is jsdom 29.1.1 to undici, marked development-only
in the lock. This is Node tooling exposure, not evidence that browser-native
fetch uses this package.

## Correction

Apply F086's targeted security-lock policy: add independent regression floors
for the four package minima first and observe each failure against the original
locks. Resolve only these packages and any strictly required transitive changes.
Preserve manifest constraints, application schemas, all scoring/gate thresholds,
generated data and workflows. Run both full gates in the foreground, individually
publish, verify exact CI and the updated dependency inventory, then confirm each
alert's authoritative fixed state. Existing Dependabot PRs 61–64 provide reference
patches, not authority to bypass local verification or broaden the update.

## Verification

All four new floors failed before either lock changed, while four earlier floors
passed. The final eight independent floor cases pass. Backend lock comparison
preserves all 81 other package records and top-level metadata; only certifi and
filelock differ. Their declared consumers accept the patched versions, neither
adds a transitive dependency, and no application SoftReadWriteLock migration was
identified. The inspected consumer uses native FileLock.

Frontend review confirms Zod 4.6.7 fits ^4.4.3 and undici 7.30.1 fits jsdom's
^7.25.0. Across 373 lock entries, only the two target versions, registry URLs and
integrity values differ. npm initially removed unrelated optional Linux libc
metadata; it was restored from the frozen baseline before verification. Both
manifest files remain unchanged. Node modules contain the intended versions.

A local SSL-context inspection of the updated certifi bundle finds the affected
emSign ECC Root CA - G3 absent while the unrelated G1, C1 and C3 roots remain.
This is a bundle-content check, not evidence about past TLS interception.
Data and frontend reviews approved the targeted scope. Standalone frontend
checks passed, then fresh foreground make check-all passed 14,838 backend tests
(97.42% coverage), 746 frontend tests (97.88%) and all lint/format/type gates.

Receipts: /tmp/qf-w43-s34-security314-red.log,
/tmp/qf-w43-s34-security314-backend-delta.json,
/tmp/qf-w43-s34-certifi-bundle-smoke.json and
/tmp/qf-w43-s34-check-security314.log. No scientific source/schema, validation
threshold, generated record, manifest constraint or workflow changed.
