# ADR-133: Share range validation across research APIs

- **Status:** Accepted
- **Date:** 2026-09-26
- **Deciders:** Codex autonomous session 25 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-063
- **Extends:** ADR-119 and ADR-132

## Context

ADR-132 made ingest requests valid timezone-aware non-empty intervals before adapter access, but
the same `start_date`/`end_date` shape is repeated by backtest, validation, Monte Carlo, and bars.
Those APIs still reach cache-aside or read-only repository code with naive, equal, or reversed
bounds. A cache miss eventually invokes the protected ingestion pipeline, while a cache hit does
not, so request semantics depend on repository state.

## Options Considered

1. **Share one validator across all public range-bearing API models and query handlers.**
   - Pro: one stable half-open interval contract; malformed requests return 422 before repository
     or adapter access; direct pipeline callers remain protected.
   - Con: the query-parameter bars endpoint must call the validator explicitly because it has no
     request body model.
2. **Rely on the ingestion pipeline for cache-aside endpoints.**
   - Pro: no model changes.
   - Con: cache hits bypass the check and every malformed request touches the repository first.
3. **Let each repository validate ranges.**
   - Pro: centralizes storage behavior.
   - Con: couples a public request invariant to repository implementations and leaves body-schema
     validation inconsistent; adapters and direct callers still need the rule.

## Decision

Generalize ADR-132's pure helper to `validate_request_range(start, end)`. Keep the ingestion
pipeline call before adapter access. Add an after-model validator to `BacktestRequest`,
`ValidateRequest`, and `MonteCarloRequest`, and retain it on `IngestRequest`. Call the same helper
at the start of the `/bars` handler before `repository.get_bars`. FastAPI converts the helper's
`ValueError` to 422 for body models; the bars handler translates it to `HTTPException(422)`.

Both bounds must be timezone-aware and satisfy `start < end`. Aware non-UTC offsets remain valid
absolute instants. No valid request, cache policy, data-quality heuristic, or threshold changes.

## Consequences

- Every public range-bearing API shares one interval contract.
- Naive, zero-width, and reversed requests fail before repository or adapter access regardless of
  cache state.
- The direct ingestion pipeline remains independently safe.
- Future range-bearing endpoints must reuse the same helper rather than repeat validators.

## Reversal

Remove the shared model and handler checks. That would restore cache-state and repository-dependent
request behavior and is not recommended.
