# ADR-381: Annualize valuation growth over elapsed fiscal-year labels

- **Status:** Accepted
- **Date:** 2026-10-27
- **Deciders:** Codex autonomous session5, ISO2026-W44
- **Resolves:** FINDING-323
- **Extends:** ADR-022; distinct from ADR-116/117 and FINDING-322

## Context

The valuation estimator passes fiscal-year observations into a private CAGR
helper whose exponent uses record count minus one. Canonical parsing permits
missing fiscal years. FY2020/FY2024 observations of 100 and 120 therefore report
20% growth rather than approximately 4.66% over four reported year intervals.
The default DCF clamps that 20% to 12%, yielding 242.81 per share instead of
179.71 with the same endpoint data and native DCF arithmetic. No actual affected
company, experiment or false graduate is established. Independent research/data
reviews reproduced the synthetic parser-to-score path before adoption.

## Options Considered

1. **Use elapsed fiscal-year-label span (chosen).** Endpoint CAGR need not assume
   an observation exists in every intervening year. The integer denominator is
   identical to record count minus one for consecutive labels, preserving native
   arithmetic there. Labels remain conditional metadata, not verified durations.
2. **Return None for gaps.** This avoids assigning elapsed label years but silently
   invokes the DCF's terminal-growth fallback despite usable labeled endpoints.
   It discards information and changes fallback policy rather than correcting CAGR.
3. **Require actual dates or reconstruct fiscal years from observation end dates.**
   This could support a separately defined duration estimator, but F322 shows
   that period identity is unresolved. Instant concepts, fiscal calendars and
   restatements need separate source evidence. Do not invent that policy here.
4. **Keep count-based arithmetic and relabel growth per observation.** DCF growth
   is projected annually, so per-observation growth is incompatible with its use.

## Decision

At estimate_growth, preserve None for fewer than two rows. For two or more rows,
require strictly increasing reported fiscal_year labels before inspecting any
candidate series; duplicate or descending labels raise ValueError. Do not sort,
deduplicate or convert malformed ordering into terminal-growth fallback.

Pass last fiscal_year minus first fiscal_year explicitly to the private _cagr
helper. Use that positive integer in the existing reciprocal exponent. Retain
all existing observed-series eligibility (every observed value present and
positive), FCF/net-income/revenue precedence, native endpoint arithmetic, growth
clamps, fallback flags, DCF projections, assumptions and valuation composition.
No missing intervening observation or positive value is inferred.

This is annualization over reported fiscal-year labels only. It does not establish
physical observation durations, correct upstream period assignment, PIT truth or
economic consistency. The guard belongs to estimate_growth, not the History model;
existing early DCF base/shares refusals can occur before the estimator is called.
No schema, parser, gate threshold, accounting-v14 or generated-record changes.

## Consequences and verification

Gapped label histories receive an elapsed-label CAGR and may change downstream
DCF/valuation results. Consecutive histories preserve the original expression
with the same integer denominator. Malformed multi-row estimator inputs refuse
explicitly. Empty/single-row estimator behavior and DCF early-return paths remain.
No historical valuation or underlying source history is reconstructed or rewritten.

Write failing gap, canonical-parser, integrated DCF/score and malformed-label tests
before source edits. Use Hypothesis to verify that removing interior observations
with fixed labeled endpoints does not change estimated growth. Replay 75 complete
ordinary claims and inspect exact source scope, obtain independent final reviews,
run make check-all in the foreground, publish individually and verify exact CI.
Reversing the helper denominator and removing the estimator guards restores the
prior behavior and reopens F323; do not edit this accepted ADR.
