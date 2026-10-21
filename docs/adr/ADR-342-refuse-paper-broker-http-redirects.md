# ADR-342: Refuse automatic redirects for authenticated paper-broker requests

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 13, ISO 2026-W43; independent research review
- **Extends:** ADR-021, ADR-341
- **Resolves:** FINDING-290

## Context

ADR-341 validates the initial canonical paper origin. The adapter still uses
urllib's default redirect handling, which can construct a follow-up request to
another origin while retaining the APCA authentication headers. An installed
standard-library handler reproduced that forwarding with synthetic headers;
no real redirect, server, credential exposure or order is established.

Independent synthetic opener pipelines verified a refusal mechanism for GET
and POST, statuses 301/302/303/307/308 and same/other-origin destinations. Each
used one fake initial response and zero follow-up calls, preserved the request
and raised native HTTPError with its original status, URL and response body.

## Options considered

1. Refuse every automatically followed redirect using a private redirect handler
   in a local default opener. Small fail-closed policy, no target interpretation
   or authentication-header rewrite; same-origin redirects fail too.
2. Follow only same-origin redirects. More flexible but adds destination parsing,
   redirect method/body policy and a second URL-identity boundary without a
   demonstrated broker requirement.
3. Strip authentication on cross-origin redirects. Prevents that particular header
   forwarding but still permits nonpaper transport and changes response semantics.
4. Retain default redirects. Leaves the demonstrated forwarding behavior intact.

## Decision

Use a private HTTPRedirectHandler subclass whose redirect_request returns None.
Open each existing Request with build_opener(handler).open instead of urlopen.
The default error chain then raises HTTPError without opening the redirect
target. Refuse same-origin and other-origin automatic redirects alike; statuses
not automatically followed by urllib retain their native error behavior.

Preserve original request URL, method, JSON bytes, authentication/content headers,
timeout, response JSON decoding, constructor and reconciliation. Default proxy,
TLS and error handlers remain; add no retry, URL fallback, warning filter or
alternate endpoint. The explicit injected fetcher continues to define a custom
transport and is unchanged.

## Consequences and limits

A broker redirect now aborts the invocation before its follow-up transport.
This may defer subsequent orders and the later snapshot; it cannot roll back
an earlier request or establish whether a server already processed an order.
No liquidation, retry or transaction policy is added.

A fresh local opener intentionally bypasses globally installed urllib opener
customizations. No repository install_opener caller exists; use the existing
fetcher injection for explicit custom transports. Each default request creates
its own opener. DNS/proxies, server authenticity and credential validity remain
outside this boundary; tests use synthetic literals and blocked fake handlers.

Require actual old-adapter RED through synthetic responses before implementation,
then exercise the real opener/error chain rather than testing return None alone.
Adapt the initial-origin Request interception to OpenerDirector.open while
preserving its assertions. Independent review, prior-body compatibility and fresh
foreground make check-all precede publication. No real service, credential,
generated record, research formula, threshold, accounting identity or frozen
cohort changes. Reversal restores default urlopen and reopens FINDING-290.
