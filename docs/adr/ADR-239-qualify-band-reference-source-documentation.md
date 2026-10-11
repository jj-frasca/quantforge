# ADR-239: Qualify source documentation of band reference strategies

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 31, ISO 2026-W41
- **Relates to:** ADR-042, ADR-055, ADR-061, FINDING-155, FINDING-159

## Context

FINDING-159 and the UI qualify band scores as historical latent/filtered references,
but source docstrings still call the filtered state MMSE, the reference an upper
bound, and the latent/filtered gap unrecoverable edge. PlantedEdge describes its
band log-mean as a simple-return mean, while the generic scorer describes every
supplied sign strategy as that conditional simple-mean strategy. Those claims
exceed the written evidence and can mislead the next scientific implementation.
Generator notes also conflate stationary log-return variance normalization with
realized volatility and leave the predictable-variance fraction ambiguous.

## Options Considered

1. Qualify source-facing documentation under the existing written findings.
   Reversible and behavior-preserving, but leaves mathematical correction Open.
2. Correct return means, posterior variance and initialization here. Requires a
   separately attributed test-first methodology contract; rejected for this slice.
3. Leave source claims until mathematical correction. Preserves misleading promises.

## Decision

Describe oracle_sharpe_of as scoring supplied lagged sign-reference predictions
against simple returns and turnover costs. Identify historical band fields as
latent conditional log-mean and filtered log-mean-rule references. Describe filtered_deviation
as the specified causal Kalman recursion, with its existing initialization and
startup convention. Remove unsupported optimality, upper-bound and unrecoverable-
edge statements. Qualify the generator normalization and predictable fraction as
stationary log-return model quantities, without a simple-return or Sharpe bound.
Keep the caller's prior-information/predicted-bar contract clear.

Change only docstrings and explanatory comments. Retain every executable AST node,
signature, field name, seeded draw, default, source/filter/reference computation,
threshold, fingerprint and historical artifact. FINDING-155 and FINDING-159 remain
Open; this qualification does not certify the posterior or correct log/simple mean.
Record this follow-up in the existing F159 finding and cold memory rather than
creating a duplicate methodology finding.

## Verification

Before editing capture the published module AST with docstrings excluded. After
editing require exact equality of that executable AST and independent wording
review against F159's derivation. No tests asserting wording or mirroring comments
are added because runtime behavior is unchanged. Run the required full foreground
make check-all, individual explicit-path delivery and exact master CI.

## Consequences and reversal

Source readers receive the same scientific qualifications as UI readers while
historical scores retain their meaning. Reverting the wording would restore the
misleading claims; the open findings and mathematical correction still require
separate governance.
