# ADR-265: Refuse original infinite rank-IC scores

- **Status:** Accepted
- **Date:** 2026-10-12
- **Deciders:** Codex autonomous session 3, ISO 2026-W42
- **Resolves:** FINDING-214
- **Extends:** ADR-035, ADR-260, ADR-264

## Context

The shared portfolio ranker refuses original infinite factor scores, but direct
rank_ic treats them as ordinary ranked observations. Multiple overflowed values
become false ties and publish finite IC/summary evidence. Production search calls
the portfolio kernel first and already refuses these inputs; the demonstrated
gap is the public IC helper's intrinsic evidence boundary.

## Options Considered

1. Refuse exact signed infinity after existing checked-price preparation and before
   pairwise masking/ranking.
   - Pro: consistent with ADR-260 without changing native finite ranks or NaN warmup;
     existing column and price/calendar refusal precedence remains.
   - Con: declines an infinite score even when its date has no next return.
2. Rely on the portfolio caller or drop infinity as missing.
   - Pro: no direct helper guard, or computation can continue.
   - Con: publishes invalid direct evidence, or silently changes the scored universe.
3. Recover every factor or add a broad score dtype/domain rule.
   - Pro: potentially handles more arithmetic/input issues.
   - Con: changes unrelated generators or accepted inputs beyond this finding.

## Decision

After ordered-column matching and asset_returns(prices).shift(-1), but before
scorable-mask construction and either average-rank helper, refuse any exact positive
or negative infinity in the original signals using native DataFrame membership.
No float conversion. Refuse even final-only, singleton and otherwise unscorable
infinities; those are invalid original evidence, not NaN warmup. Keep original
NaN/pd.NA exclusion, finite native wide/integer/nullable/object numeric/bool inputs,
empty panels, average ties, native pre-mask preservation, paired dates, undefined-
date dropping and all correlation/summary formulas unchanged.

This is an infinity-only policy. No dtype ban, finite-range cap, clipping, source
repair, calendar rule, summary-domain rule, estimator or gate threshold change.
Existing unsupported payloads remain unsupported. Price/calendar errors retain
priority after column identity, and the guard precedes rank computation.

## Consequences, identity and reversal

A direct helper cannot publish finite IC from overflowed or explicit infinite
scores. Canonical production generators retain exact outputs; portfolio-first
search already refuses the same source under ADR-260, so no changed graduate or
historical contamination is inferred. IC neither gates nor selects/sizes, and is
separate from the longitudinal calibrated pipeline; calibration identities and
generated records stay unchanged. Other precision/source-domain limitations remain.

Observe signed-infinity RED before code across native/nullable/wide/Decimal and
masked-away observations. Verify refusal before ranking, source-error precedence,
NaN/pd.NA/native finite/empty compatibility, strict caller state, an adversarial
Hypothesis invariant and all generators with independent review. Run foreground
make check-all, deliver individually and watch exact CI. Remove only the exact-
infinity guard to reverse this correction and reopen FINDING-214.
