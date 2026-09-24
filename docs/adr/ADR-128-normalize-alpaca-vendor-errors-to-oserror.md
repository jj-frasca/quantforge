# ADR-128: Normalize Alpaca vendor errors to `OSError`

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 104
- **Resolves:** FINDING-056

## Context

`AlpacaDataAdapter`'s docstring claims the same error-handling pattern as `YFinanceAdapter`, which
normalizes any non-`(ValueError, KeyError, OSError)` fetch/parse exception into `OSError` so callers
have one consistent exception type to catch. `AlpacaDataAdapter.fetch_price_bars` had no such guard
at all — the docstring's claim was false.

## Options Considered

1. **Mirror `YFinanceAdapter._fetch_once`'s exact guard shape**: `try`/`except (ValueError, KeyError,
   OSError): raise`, then `except Exception as exc: raise OSError(...) from exc`.
   - Pro: makes the docstring's existing claim true, matches an established, already-reviewed
     pattern exactly rather than inventing a new one.
   - Con: none identified.
2. **Only catch and wrap specific known Alpaca exception types** (e.g. `urllib.error.HTTPError`).
   - Con: narrower than yfinance's own guard, which deliberately catches anything unanticipated —
     the whole point of the pattern is defending against vendor exception types not yet seen in
     production, not an enumerated list.

Chose option 1: identical shape to the sibling adapter, which is already this codebase's reviewed,
incident-informed convention.

## Decision

`fetch_price_bars`'s fetch + map + normalize sequence is wrapped in a `try`/`except`: `ValueError`,
`KeyError`, and `OSError` re-raise unchanged (already-expected types this codebase's resilient
callers handle); anything else is wrapped into `OSError(f"Alpaca fetch failed for {symbol!r}:
{type(exc).__name__}: {exc}")`.

## Consequences

- `AlpacaDataAdapter.fetch_price_bars` now actually matches its own docstring's claim.
- Any vendor-specific or parse-level exception not already `ValueError`/`KeyError`/`OSError`
  surfaces as a clean, consistently-typed `OSError` instead of a raw vendor exception type.
- A missing/malformed payload field still raises a bare `KeyError` (matching `YFinanceAdapter`'s own
  established convention: `KeyError` is already "a kind the resilient hunt handles," not
  double-wrapped).

## Reversal

Remove the `try`/`except`. Not recommended — reintroduces FINDING-056's docstring/behavior mismatch
and loses consistent error typing for any consumer of this adapter.
