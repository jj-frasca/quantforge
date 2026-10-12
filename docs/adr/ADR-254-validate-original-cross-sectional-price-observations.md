# ADR-254: Validate original cross-sectional price observations

- **Status:** Accepted
- **Date:** 2026-10-11
- **Deciders:** Codex autonomous session 35, ISO 2026-W41
- **Resolves:** FINDING-203
- **Extends:** ADR-024, ADR-178

## Context

Public cross-sectional asset_returns accepts raw panels outside ResearchDataset.
Missing prices become zero returns through pct_change/fillna, negative-price growth
becomes positive performance, and invalid first/singleton observations disappear
behind the legitimate first-period zero. These finite returns reach portfolio sums.

## Options Considered

1. Validate original observations at the shared asset-return boundary.
   - Pro: public asset and portfolio paths share intrinsic source validity.
   - Con: performs one native validation pass per populated panel.
2. Rely on quality-gated production providers.
   - Pro: no additional kernel work.
   - Con: direct research callers can still fabricate finite return evidence.
3. Fill/drop/convert invalid observations.
   - Pro: may permit computation to continue.
   - Con: invents evidence, alters the calendar or narrows native price precision.

## Decision

For populated panels, asset_returns requires each original column to have a real
nonboolean numeric dtype and every observed price to be nonmissing, finite and
strictly positive, before pct_change. Validate native columns without converting
prices to float64. Retain the original frame and exact native pct_change/fillna
operation. Zero-cell panels keep their original behavior; positive singleton
panels retain the defined first-period zero.

Object/string/complex/boolean sources refuse rather than being coerced. Complete
nullable numeric, integer and wider native numeric prices remain supported. Do not
change calendars, signals, ranking, lags, costs, estimators or validation thresholds.
Extreme finite derived-return representability remains a separate boundary, as in
ADR-178; this decision does not claim to solve it.

## Consequences and reversal

Missing or nonsensical source prices cannot become finite asset/portfolio evidence,
including when exposure is zero. Production quality-gated inputs already satisfy
these intrinsic rules. Valid input arithmetic, empty panels, generated records and
search/gate policy remain unchanged. Remove the source guard to reverse this
correction and reopen FINDING-203.
