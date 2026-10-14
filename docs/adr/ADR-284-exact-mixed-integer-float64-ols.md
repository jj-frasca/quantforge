# ADR-284: Preserve exact OLS coefficients for mixed integer/Float64 sources

- **Status:** Accepted
- **Date:** 2026-10-13
- **Deciders:** Codex autonomous session 9, ISO 2026-W42
- **Resolves:** FINDING-233, remaining mixed-family coverage of FINDING-232
- **Extends:** ADR-283

## Context

ADR-283 repairs both-original Float64 coefficients but deliberately excludes mixed
source families. The same large-origin benchmark2**60+arange4*256 and strategy
benchmark+256 still publish beta2/3 and annual alpha9.684540638697531e19 when
one original source is supported integer and the other Float64. Exact represented
OLS gives beta1/alpha64512. Float conversion also erases distinct integer neighbors
before covariance, so converting integers to reuse Float64 moments is inadequate.

## Options considered

1. Reuse exact common-grid coefficients with exact integer ratios and mixed-only
   dispatch. Minimal arithmetic change, preserves prior family paths; deliberately
   changes every admitted mixed family's coefficient rounding.
2. Convert integers to float64 before ADR-283. Smaller code, but discards the
   integer distinctions responsible for the demonstrated error.
3. Add a separate duplicate accumulator. Clear separate helper, but repeats exact
   covariance/intercept logic and increases maintenance without isolation benefit.
4. Repair every mixed floating family. Broader consistency but larger scope than
   this integer/Float64 evidence, including narrow/wide/third-party contracts.

## Decision

Only original aligned pairs with one supported native/classic integer and one
native float64/classic Float64 receive ADR-283's coupled exact OLS helper. Supported
integer means native NumPy dtype kind i/u or classic pandas Int/UInt8/16/32/64.
Use a local ratio adapter returning (int(value),1) for Python/NumPy integer scalars;
retain original floating as_integer_ratio exactly. Never convert an integer to
float. The same maximum binary denominator grid and unchanged sufficient sums
then calculate final beta and annual alpha, including constant-source beta0 and
exact strategy mean. Final coefficient overflow/nonfinite refusal and legitimate
zero/subnormal rounding remain the existing ADR-283 contract.

Keep prior both-integer ADR-275/276 dispatch, both-Float64 ADR-283 results, native
narrow/wider and all third-party/mixed-other paths exactly. Original validation,
excess/IR/TE/drawdown/metadata/state remain. Already-rounded mixed subtraction
retains its separate precision limit; exact source coefficients do not establish
exact excess evidence. No threshold, calibration identity, generated records,
workflow, persistence shape or source policy changes.

## Evidence and limits

Independent read-only prototype:352finite Fraction helper pairs/32overflow
refusals across all16integer dtypes, two Float64 dtypes and both directions;
288public exact coefficients with accepted baseline other outputs unchanged;
420complete outside-family baselines,64full-width/tiny/rounding controls.
100k mixedUInt64/Float64 .24s. Integer encoded width<=1138bits with grid<=2**1074;
Float64's2098bit bound dominates, retaining ADR-283's conservative6600bit
intermediate bound for n<=sys.maxsize. Streaming scans have O(n) time/O(1)
accumulator count without cache/object Series/Fraction production values.

Require original integer neighbors unrepresentable in float64, all16dtypes/both
directions/masked NumPy scalar iteration, centeredFraction/Hypothesis public RED,
constants/full-width/tiny/final overflow/zero-subnormal controls, source guards/
alignment/ownership/state, both predecessor and all outside-family preservation,
independent final review, foreground make check-all and exact master CI.
Family-wide rounding intentionally changes. Historical market contamination is
not established, and unrelated statistic availability/precision remains outside.

## Reversal

Remove mixed eligibility and restore direct floating scalar ratios in the helper.
This reopens FINDING-233 while preserving ADR-283's both-Float64 and ADR-275/276's
both-integer coefficients.
