# ADR-178: Validate backtest price observations

- **Status:** Accepted
- **Date:** 2026-10-07
- **Deciders:** Codex autonomous session 11, ISO 2026-W41
- **Resolves:** FINDING-110
- **Extends:** ADR-007, ADR-167, ADR-176, ADR-177

## Context

The public engine accepts Series outside the canonical dataset boundary. Missing prices become
zero returns through pct_change/fillna; negative prices can report positive performance. First-row
and singleton invalid values are also hidden by the legitimate first-period zero return.

## Options Considered

1. Validate supplied prices before calculating returns. All direct callers share intrinsic validity.
2. Fill or drop invalid rows. This invents observations or changes the execution calendar.
3. Rely on ResearchDataset. Public engine callers need not construct that model.

## Decision

Require real nonboolean numeric price dtype, finite observations and strictly positive prices
before pct_change. Match ADR-167's dtype policy; reject object/string/complex/boolean inputs rather
than coercing them. Complete nullable numeric Series remain valid. Keep the original Series for
return calculations, first-period zero return, calendar checks, signal alignment/clip/fill, lag,
turnover, costs, metrics and scaled-wealth checks. Empty numeric histories remain supported.

## Consequences and limits

Invalid supplied evidence raises ValueError even for zero exposure or a singleton. No prices are
filled, dropped, capped, floored or repaired. The guard does not establish acquisition lineage,
daily cadence or strategy causality, nor guarantee that extreme finite price ratios are representable.
Generated data, validation thresholds, estimators and workflows do not change.

## Reversal

Remove the intrinsic price checks. This reopens FINDING-110.
