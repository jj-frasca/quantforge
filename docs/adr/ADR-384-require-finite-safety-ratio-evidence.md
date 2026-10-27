# ADR-384: Require finite safety-ratio evidence

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session7, ISO2026-W44
- **Resolves:** FINDING-326 within ordinary numeric SafetyScore construction
- **Extends:** ADR-029/155/373

## Context

Ordinary SafetyScore construction admits NaN/infinity in its nullable leverage
and liquidity ratios. NaN liquidity clips to maximum safety, yielding a finite
quality0.5 accepted by FundamentalRecord in a synthetic current-history witness.
The component itself serializes as null. Extreme finite source arithmetic can
also overflow. No actual vendor incidence, graduate or trading effect is known.
Independent data and research prospective reviews approve this bounded correction.

## Options Considered

1. **Require finite numeric SafetyScore fields (chosen).**
   - Pro: direct, JSON and actual producer share one refusal before clipping or
     distress comparisons; existing finite values and missingness remain.
   - Con: previously accepted infinite saturation now refuses; sweep scoring can
     fail its shard, and upstream invalidity yielding finite/boolean output stays.
2. **Clamp or convert invalid ratios to None.**
   - Pro: preserves consumer availability.
   - Con: invents scores or missingness and can turn a valid distress veto into
     keep-unscored permission; no recovery or missingness policy is justified.
3. **Validate all AnnualFundamentals inputs or redesign all quality math.**
   - Pro: could cover earlier erased invalidity and precision failures.
   - Con: changes shared valuation/provider semantics and requires a separate
     invalid-versus-unavailable policy, compatibility evidence and ADR.

## Decision

Add only allow_inf_nan=False to SafetyScore's existing ConfigDict. Keep frozen,
nullable absence, boolean retained-earnings flag, finite values/coercions, fields,
JSON shapes and every arithmetic/clip/distress threshold unchanged. ValidationError
from financial_safety propagates. In particular, make_distress_provider keeps
consumer evaluation outside its existing acquisition try; no new catch/fallback.
No schema revalidation of existing instances or unchecked model copies is adopted.

## Consequences

New numeric safety claims refuse nonfinite components before they can disappear
behind finite quality. Existing quality/record/distress producer calls refuse too.
A finite insolvency veto plus invalid liquidity becomes an explicit error, never
ordinary None fallback. A sweep may fail before writing its shard; no per-record
skip or partial-output policy is introduced. Finite-source overflow is refused,
not numerically recovered. Retained-earnings NaN-to-bool and nonfinite operands
that produce finite ratios remain outside this boundary. No source-period/PIT,
F-score methodology, ratio-domain, threshold, v14 or generated-data change occurs.

Write actual failing constructor/JSON and producer/provider tests before the
single keyword patch. Include finite/None/coercion controls, Hypothesis finite
round trips, and the invalid-liquidity plus finite-distress-veto case. Replay the
324 ordinary complete claims, 14 config/JSON controls and whole quality-module
AST except the keyword. Obtain final independent data/research review, foreground
make check-all, individual safe sync/push and exact CI verification.

## Reversal

Remove the SafetyScore finite keyword. That reopens FINDING-326 and does not
repair any historical erased component evidence.
