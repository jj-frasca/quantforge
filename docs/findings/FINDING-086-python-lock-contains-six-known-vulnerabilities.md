# FINDING-086: The Python lock contains six known vulnerabilities

- **Severity:** Critical — one critical, one high, and four medium Dependabot alerts are open
- **Status:** Resolved
- **Date:** 2026-10-02
- **Affects:** `backend/uv.lock`

## Finding

GitHub's Dependabot API identifies six open alerts in four locked packages:

| Package | Locked | Patched | Alerts | Highest severity |
|---|---:|---:|---:|---|
| `anyio` | 4.13.0 | 4.14.2 | 2 | Critical |
| `virtualenv` | 21.7.12 | 21.7.13 | 1 | High |
| `soupsieve` | 2.8.4 | 2.9.0 | 2 | Medium |
| `pydantic-settings` | 2.14.1 | 2.14.2 | 1 | Medium |

The advisories cover TLS certificate spoofing for IDNA hostnames and process-pool stderr deadlock in
AnyIO, activation-script command injection in virtualenv, two quadratic selector-parser denial of
service paths in Soup Sieve, and out-of-tree symlink reads in nested pydantic-settings secrets.

Current QuantForge usage narrows several exploit paths: outbound service domains and BeautifulSoup
selectors are code-owned, no nested secrets source is configured, and virtual environments are
locally created. Those facts reduce present exposure but do not justify retaining vulnerable
transitive code, especially when exact patched releases and already-green Dependabot PRs exist.

## Required correction

Update only these four lock entries to at least their first patched releases. Preserve application
constraints and avoid opportunistic package upgrades. Add a lock-floor regression for the exact
security minima, run the full repository gate, then verify the open-alert API after delivery.

This correction changes no application behavior, validation threshold, generated data, workflow,
credential, or external resource.
