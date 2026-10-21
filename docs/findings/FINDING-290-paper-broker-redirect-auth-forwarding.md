# FINDING-290: Default paper-broker redirects can forward authentication headers

- **Status:** Resolved — ADR-342; actual-adapter regressions and full verification passed
- **Date:** 2026-10-21
- **Scope:** `execution/alpaca_broker.py::_request`; ADR-021/341

## Evidence

The broker's canonical initial origin does not constrain urllib's default
redirect handler. Direct execution of the installed HTTPRedirectHandler on a
synthetic GET request and 302 response constructs a Request for `other.invalid`
with both APCA authentication header names retained. Only synthetic header
values were supplied; no transport, real credential or external account was used.
This establishes a possible follow-up route, not an observed broker redirect,
credential leak, live account access or production incident.

Parent receipt: `/tmp/qf-w43-s13-redirect-scope.json`.
Independent receipt: `/tmp/qf-w43-s13-redirect-independent.md` and `.json`.
Twenty synthetic real-opener pipelines establish the prospective refusal
mechanism across GET/POST, 301/302/303/307/308 and same/other origins, with one
initial fake call, zero follow-ups and native HTTPError. These scope probes are
distinct from preimplementation actual-adapter regression evidence.

## Correction and boundaries

ADR-342 supplies a private redirect handler returning None in a local default
opener. The normal urllib error chain refuses automatic redirects before a
follow-up transport; same-origin redirects also refuse. Request construction,
JSON, timeout and nonredirect/error semantics remain. Default proxy/TLS handlers
remain; global install_opener customization is deliberately bypassed. Explicit
fetcher injection stays available and outside this default transport policy.

A refusal cannot undo an earlier request or determine whether a server already
processed an order. Later orders and snapshot appending may be deferred. There
is no retry, rollback, liquidation, credential-validation or DNS/proxy guarantee.
All verification blocks real HTTP and uses synthetic response objects and keys.

## Verification

Before the runtime edit, actual-adapter tests produced 17 failures with 40
passing controls (`/tmp/qf-w43-s13-redirect-red-final.log`): sixteen follow-up
attempts and one global-opener policy case. The application diff was empty.
An earlier attempt also had three test-hook signature failures; the interception
was corrected for legacy positional arguments before the runtime change, while
all original origin assertions stayed intact. Combined focused verification
then passed 88 cases with two existing live smokes excluded
(`/tmp/qf-w43-s13-redirect-green.log`).

Independent final seven-path review approved the change and passed 86 focused
tests. Forty-four actual-adapter fake pipelines covered twenty redirect cases,
four successes and twenty native 4xx/5xx cases. Each used one synthetic initial
response and zero follow-ups, preserving method, payload, headers, timeout,
error code, original URL and body. Real HTTP do_open was blocked throughout.
Default handlers remain except the redirect substitution, and the global custom
opener sentinel was bypassed. Prior runtime AST is unchanged outside declared
imports/helper/opener/documentation; 288 other pre-existing backend test files
and all other origin-test function ASTs remain intact. Receipts:
`/tmp/qf-w43-s13-redirect-review.md`, `-review.json`, `-parent-audit.json`.
Runtime SHA256:
`7be208b910e439ae3c378c6e8ebcf68beb8edd1506978c6866a9842b472be184`.

Fresh foreground `make check-all PYTEST_WORKERS=2` passed 13,811 backend tests
(97.38% coverage), 566 frontend tests (97.83% statements), lint, formatting and
strict types (`/tmp/qf-w43-s13-check342.log`). All local verification closed
before individual publication; exact master CI is checked after the push.
No real service, credential, order, generated record, research threshold, search
identity, accounting version or frozen cohort changed.
