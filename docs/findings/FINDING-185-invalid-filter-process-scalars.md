# FINDING-185: Invalid band-filter process scalars can produce finite scores

- **Date:** 2026-10-11
- **Severity:** Medium — invalid process evidence can appear measured
- **Status:** Corrected by ADR-235
- **Affected:** filtered_deviation original process parameters
- **Reproduced revision:** 4df9f946de0635e326927c52885267af9b747a3e

## Reproduction

On logarithms of closes [100,101,100,101,100], the filter accepts level_vol=NaN,
deviation_vol=NaN and drift=NaN. Each yields all-missing estimates; the established
lagged filter forecast then yields reference Sharpe zero because missing means
are flat. With level_vol=+Inf, estimates are [NaN,0,0,0,0] and the same reference
pipeline yields finite Sharpe about -4.085063. Boolean process inputs also produce
finite states. Independent review reproduced these direct-call defects after the
source-only ADR-234 guard. No corrupt committed artifact, new search or changed
power count is inferred.

## Correction boundary

ADR-235 validates original finite real nonboolean process scalars without
substituting converted operands. Keep the existing stationary/volatility ranges,
original negative comparisons, signed drift, zero level volatility and all valid
native source/filter/reference behavior. Parameter fitting, initialization,
derived arithmetic, reference optimality, thresholds and records stay separate.
FINDING-159 remains Open.

## Verification

Final TDD observed 98 failures and 28 preserved cases before the four calls.
Parent affected verification passed 325 tests. Independent review verified 144
checks: 90 exact old/new nonconstant-source native estimate/ownership comparisons
across Python, NumPy and Fraction operands; 24 unchanged band-producer fields;
24 exact gross/net references; six range/precedence checks. Removing exactly the
four calls restores the previous filter AST. Independent final review approved all
five paths; its focused suite passed 376 tests. Full foreground make check-all
passed 4394 backend and 363 frontend tests, with lint, types and coverage green.
