# FINDING-289: Paper-broker base URL guard accepts nonpaper origins

- **Status:** Resolved for initial base URL — ADR-341; redirect policy remains separate
- **Date:** 2026-10-21
- **Scope:** `execution/alpaca_broker.py::AlpacaBroker.__init__`; ADR-021

## Evidence

The constructor's `_PAPER_HOST in base_url` test checks occurrence, not authority.
For example, the inert string
`https://api.alpaca.markets/v2/orders#paper-api.alpaca.markets` passes.
Appending `/v2/orders` puts that suffix inside the fragment. Python's actual
`urllib.request.Request` still has host `api.alpaca.markets`, POST method and
selector `/v2/orders`. The parent's synthetic submit path intercepted every
`urlopen` call before transport. Independent review reproduced the same Request
without invoking any transport. This disproves the initial destination guard's
claimed structural protection; it does not establish an actual configured URL,
live account access, credential disclosure, broker order or production incident.

Parent receipt: `/tmp/qf-w43-s13-broker-origin-witness.json`.
Independent 13-case scope receipt: `/tmp/qf-w43-s13-origin-scope.json`.
The production driver passes its fixed canonical HTTPS paper constant.

## Correction and boundaries

ADR-341 replaces substring membership with equality to the canonical HTTPS paper
origin after the existing trailing-slash trim. Keep the native constructor body,
stored URL, injected transport, request construction and reconcile logic intact.
Canonical URLs and trailing slashes remain valid; alternate components/spellings
including explicit port 443 deliberately refuse. This adds no URL normalization.

The guard covers the initial base URL. At ADR-341 adoption, urllib redirect handling
remained a separate limitation, so the module must not claim transport-wide impossibility
of reaching another endpoint. DNS/proxy behavior and credential validity are
also outside this evidence. All tests use inert strings, synthetic credential
literals and fake/intercepted transports, never external services or real keys.

ADR-342 / FINDING-290 later addresses the separate default redirect policy with
native HTTPError refusal before a follow-up request. The evidence and initial-URL
correction above retain their original scope.

## Verification

Before the runtime edit, the new suite produced 22 failures and eight passing
controls (`/tmp/qf-w43-s13-origin-red.log`), with the application diff empty.
The corrected predicate then passed all 30 new cases, including a generated
authority property and actual Request interception. Combined focused tests
passed 129 cases with two existing live smokes excluded
(`/tmp/qf-w43-s13-origin-green.log`).

Independent final five-path review approved the change and passed 59 focused
cases with those live tests excluded. Twelve accepted trailing-slash variants,
24 old/new account controls and ten independent refusal cases passed. Prior
runtime AST is unchanged except the declared predicate, error text and module
documentation; 288 pre-existing backend test files remain byte-identical.
Receipts: `/tmp/qf-w43-s13-origin-review.md`, `-review.json` and
`-parent-audit.json`. Runtime SHA256:
`170debd803c373a9307d0c4b40cfbf4d2e4f9c04875a13248077466513c0cb3a`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13,784 backend tests
(97.38% coverage), 566 frontend tests (97.83% statements), lint, formatting and
strict types (`/tmp/qf-w43-s13-check341.log`). All local verification closed
before individual publication; exact master CI is checked after pushing.
No generated record, financial methodology, threshold, search identity, frozen
cohort, external transport, real credential or actual order changed.
