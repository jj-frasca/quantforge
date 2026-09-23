# ADR-110: Compound backtest return metrics from complete net wealth

- **Status:** Accepted
- **Date:** 2026-09-23
- **Deciders:** Codex autonomous session 8 under `.claude/CODEX_CHARTER.md`
- **Resolves:** FINDING-039
- **Supersedes in part:** ADR-108's use of arithmetic annualization as Calmar's numerator

## Context

QuantForge's engine already produces the complete per-period net-return series after position lag
and turnover costs. Its descriptive return fields do not consistently measure that wealth path.
`total_return(equity)` starts at the first post-return equity observation and can omit the initial
turnover cost. `annualized_return` uses arithmetic daily mean times 252, which is an expected-return
estimate rather than the compound annual growth of the realized backtest. FINDING-039 demonstrates
that volatility drag can make the displayed annualized return and Calmar positive while ending
wealth and total return are sharply negative. Maximum drawdown also starts from the first
post-return equity value, so an initial loss or turnover charge can disappear from Calmar's
denominator.

ADR-108 correctly chose Calmar as annual return divided by drawdown, but inherited the pre-existing
arithmetic field without testing that it shares the realized wealth path's sign. The correction is
descriptive accounting only: none of these fields enters DSR, PBO, the graduation gate, or a
calibration identity.

## Decision

Compute one finite compounded wealth factor from every net return, including the first:
`growth = product(1 + r_t)`. Total return is `growth - 1`. Annualized return is the geometric rate
`growth ** (252 / n_periods) - 1`, and Calmar continues to divide that corrected annualized return
by the magnitude of maximum drawdown. Drawdown is measured on the same compounded path after
prepending the pre-return unit-wealth baseline, so the first return participates in both return and
risk. Empty input retains the existing zero convention.

The metrics boundary rejects non-finite returns and any path whose compounded wealth is non-finite
or non-positive; a real-valued geometric annual return and the project's positive-equity contract
are not defined there. It does not clip, impute, or silently convert an insolvent path to zero.
`total_return` now consumes net returns rather than post-return equity so initial-period costs
cannot disappear through the denominator.

## Alternatives considered

1. **Keep arithmetic annualization and change only the Calmar label.**
   - Pro: no backend behavior change.
   - Con: the API and dashboard would still call a sign-reversing arithmetic estimate
     “annualized return,” and Calmar would still not be the standard wealth-relative ratio.
2. **Compute CAGR from first and last equity values.**
   - Pro: uses the visible curve directly.
   - Con: the first equity point is already post-return and post-cost; without separately carrying
     initial capital, this repeats the omitted-first-period defect.
3. **Compound the complete net-return series and fail closed outside its valid domain.**
   - Pro: uses the engine's authoritative after-cost observations, preserves the first cost, and
     makes total, annualized, and Calmar signs internally consistent.
   - Con: reported annualized returns change for every non-constant backtest, and malformed or
     insolvent return paths now raise instead of producing a misleading scalar.

## Consequences

- Total return exactly matches ending wealth relative to initial capital for valid engine paths.
- Maximum drawdown includes an initial-period loss or transaction cost.
- Annualized return and total return always share a sign; volatility drag is represented rather
  than erased by arithmetic averaging.
- Calmar uses compounded annual growth and cannot praise a realized losing path with a positive
  numerator.
- API field names and frontend shapes do not change, but their values become methodologically
  correct. No gate, threshold, calibration identity, workflow, or generated record changes.

## Reversal

Restore post-first-observation equity division and arithmetic `mean * 252` annualization. That
would reintroduce the demonstrated sign reversal and omitted initial cost and is not recommended.
