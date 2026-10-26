# ADR-380: Refuse unmeasurable parser-derived gross profit

- **Status:** Accepted
- **Date:** 2026-10-26
- **Deciders:** Codex autonomous session 3, ISO2026-W44; research/data review
- **Addresses:** FINDING-321
- **Extends:** ADR-029, ADR-117 and ADR-155

## Context

Finite synthetic revenue/COGS can overflow fallback gross-profit subtraction and
award a false improving-margin point. The downstream quality record is finite,
so finite output validation cannot identify the error. All raw values in the
witness are finite; economic plausibility and production incidence are unestablished.
An ordinary ValueError could become missing fundamentals in history providers,
so refusal must retain an arithmetic-error distinction.

## Options Considered

1. **Refuse nonfinite fallback-derived gross profit with OverflowError.**
   - Pro: stops the demonstrated producer defect before scoring, preserves direct
     GrossProfit precedence and bypasses availability fallbacks.
   - Con: no recovery of an exact value outside float64; broader history/scorer
     numeric validity remains separate.
2. **Harden every AnnualFundamentals field or every quality ratio.**
   - Pro: establishes wider numeric policy.
   - Con: changes unrelated source and provider contracts, and cannot reconstruct
     original revenue/COGS from a gross-profit infinity already stored in a model.
3. **Use exact/scaled arithmetic to recover a margin or substitute missing profit.**
   - Pro: might retain a useful ratio in this particular example.
   - Con: changes financial arithmetic or creates missingness at a producer that
     currently promises a gross-profit amount, requiring a separate recovery policy.

## Decision

Only inside the existing COGS fallback, immediately after gp = revenue - COGS,
raise OverflowError when math.isfinite(gp) is false. Keep native finite results,
direct GrossProfit selection, tag/fiscal-year precedence and all other calculations.
No Annual/history model policy or scorer change is adopted.

Add only OverflowError to fundamental_sweep.main's existing history-acquisition
per-company catch. Increment its existing error counter, skip that company and
continue. Other arithmetic errors retain their old propagation. Existing history
providers do not catch OverflowError, while the universe's existing ArithmeticError
handler records per-symbol failures before search. No None/zero fallback is added.

## Consequences

The demonstrated invalid derived profit cannot become a false finite quality
record. A sweep can still write valid later companies; its existing retention and
sole-writer policy stay. Preexisting float-conversion OverflowErrors during history
acquisition also become skipped sweep rows. The exception class reports numerical
refusal, not an independently certified cause for arbitrary bad vendor inputs.
Direct nonfinite facts, FCF arithmetic and arbitrary in-process histories remain
outside this bounded correction. No economic/PIT, historical incidence, threshold,
search, v14 or calibration claim follows.

Observe failing parser/provider/universe/sweep tests before source edits. Use a
Fraction-based Hypothesis invariant: preserve native finite subtraction; nonfinite
results refuse, with exact raw-float arithmetic witnessing an out-of-range result.
Do not promise exact subtraction for ordinary rounded outputs. Replay frozen finite
claims and source ASTs, obtain final research/data reviews and pass foreground
make check-all. Reverse the producer guard and sweep catch addition together.
