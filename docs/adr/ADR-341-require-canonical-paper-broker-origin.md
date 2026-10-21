# ADR-341: Require the canonical HTTPS paper-broker origin

- **Status:** Accepted
- **Date:** 2026-10-21
- **Deciders:** Codex autonomous session 13, ISO 2026-W43; independent research review
- **Extends:** ADR-021
- **Resolves:** FINDING-289 (initial URL guard)

## Context

The broker constructor checks only whether `paper-api.alpaca.markets` occurs
anywhere in its base URL. An unrelated authority, userinfo, path, query or
fragment can contain that text. In an inert reproduction, a base URL naming the
live authority with `/v2/orders` before a fragment containing the paper hostname
passes construction. Appending the request path inside that fragment still
constructs a POST whose authority is the live host and selector is `/v2/orders`.
The request was intercepted before transport, using synthetic credential literals;
no external request, order, real credential, actual misconfiguration or incident
is established. Production callers use the canonical fixed paper URL.

## Options considered

1. Compare the complete base URL, after existing trailing-slash trimming, with
   the canonical HTTPS paper origin. Small allowlist with no parser ambiguity;
   deliberately refuses alternate URL spellings and components.
2. Parse and allow equivalent schemes/authorities/ports and selected components.
   More flexibility, but requires a larger policy and transport-parser agreement
   for configuration shapes no production caller needs.
3. Keep substring matching. Retains a directly demonstrated guard bypass.

## Decision

Require `base_url.rstrip("/") == "https://paper-api.alpaca.markets"` before
retaining credentials or selecting the transport. Keep the existing stored-base
trimming and the rest of the adapter and reconciliation body unchanged.

Canonical origin with any number of trailing slashes remains valid. HTTP,
explicit ports including 443, trailing-dot names, userinfo, paths, queries,
fragments and suffix/subdomain authorities refuse. Uppercase hostname already
failed the old substring check; no case-normalization feature is added. This
is an explicit configuration-domain tightening, not a general URL normalizer.

## Consequences and limits

The initial request cannot select an alternate origin through the supplied base
URL. Fix the module's broader structural-impossibility claim to describe this
boundary accurately. Standard-library redirect behavior remains unchanged and
is a separate transport-policy limitation; this guard does not certify redirect
destinations, DNS/proxy behavior or credentials. No real service is used to test
this correction, and no production incident is inferred from the synthetic URL.

Observe constructor refusal RED before implementation. Protect canonical and
trailing-slash requests with an intercepted standard-library Request, and test
adversarial components and generated nonpaper authorities. Independent review,
unchanged-body checks and fresh foreground `make check-all` precede delivery.
No account access, credentials, data JSON, thresholds, search/accounting identity
or frozen-cohort changes. Reversal restores substring matching and reopens the
demonstrated defect; another URL or redirect policy needs a superseding ADR.
