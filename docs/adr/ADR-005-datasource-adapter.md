# ADR-005: DataSourceAdapter pattern

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
Vendor APIs change shape, get deprecated, and disagree with each other. The platform starts
on yfinance (no API key) and adds Polygon in Phase 3, with Reddit/NewsAPI as experimental
sources in Phase 8. Business logic must not be coupled to any vendor's wire format, and
adding a vendor should not ripple through research or validation code.

## Options Considered
1. **`DataSourceAdapter` ABC; each vendor implements it and emits canonical `PriceBar`.**
   - Pro: one seam between "the outside world" and the codebase; vendor changes are isolated
     to one adapter; new vendor = new class, zero downstream change; enables vendor
     cross-validation (quality check #8) by running two adapters over the same symbol.
   - Con: an abstraction layer to maintain; slight indirection.
2. **Call vendor SDKs directly where data is needed.**
   - Pro: least code up front.
   - Con: vendor types leak everywhere; a vendor change forces edits across the codebase;
     no natural place for normalization or quality gating.
3. **Per-vendor models passed through the system, converted late.**
   - Con: multiple shapes flow downstream; defeats the canonical-schema decision (ADR-004).

## Decision
Define a **`DataSourceAdapter` ABC** (`backend/app/data/sources/base.py`). Every source
implements it and returns canonical `PriceBar`/`FundamentalData`. Adapters normalize at
ingestion (ADR-004); nothing bypasses the adapter, and nothing normalizes at query time.

## Consequences
- yfinance is the first adapter (primary, no key). Polygon is the second (Phase 3), which is
  what makes vendor cross-validation real.
- Each adapter records an `adapter_version`, pinned into the ExperimentManifest so a backtest
  is reproducible against a known vendor behavior.
- The contract is intentionally narrow (fetch → normalized canonical rows), keeping vendor
  quirks out of research/validation entirely.
- Adapter interface details are specified in the data-engineer agent spec and
  `.claude/context/data-contracts.md` at the start of Phase 2.
