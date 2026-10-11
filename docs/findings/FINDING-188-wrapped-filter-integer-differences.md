# FINDING-188: Native integer differences can wrap into false finite filter states

- **Status:** Corrected by ADR-238
- **Date:** 2026-10-11
- **Scope:** Direct filtered_deviation integer sources after ADR-236
- **Decision:** ADR-238

## Evidence

With rho=0.5, level_vol=0.01, deviation_vol=0.02 and drift=0, uint8
[5,4,5] yields native differences [255,1] and estimates [NaN,102,74.833333].
Real differences [-1,1] yield [NaN,-0.4,0.166667]. int64 minimum followed by
maximum wraps an exact difference 2**64-1 to -1, yielding finite estimate -0.4.
Independent review confirmed unsigned wrapping and both signed overflow directions
across widths. Finite initialized/recursive quantities cannot detect lost integer
arithmetic. No corrupt committed artifact or changed cohort rate is inferred.

Conversely, uint64[max-1,max] has valid native difference one, while converting
observations to float64 before subtraction produces zero. A correction must refuse
unrepresentable native differences without replacing accepted source arithmetic.

## Correction boundary

Exact original adjacent integer subtraction must fit its original dtype's range.
Refuse otherwise; keep native np.diff on accepted arrays. Preserve signed decreases,
unsigned nondecreasing paths, masks and short histories. No float normalization,
numerical recovery, general precision guarantee or reference reinterpretation.
FINDING-155 and FINDING-159 remain Open.

## Verification

Pre-code TDD observed 25 failures and 48 preserved cases. Parent direct affected
suite passed 404 tests after the exact integer preflight. Independent review
approved 451 affected tests and 264 checks: 144 exact native integer/mask/byte-order/
boundary/ownership comparisons, 72 wrapping refusals and policy restoration, 24
unchanged producer fields and 24 exact gross/net references. Removing only the
integer preflight restores the prior filter AST.

The first full gate stopped at mypy's float64 source annotation. Inspecting the
original dtype's string descriptor fixed typing without source conversion; 12
independent descriptor comparisons confirmed identical bounds. All 73 integer
tests passed again in parent and independent runs; fresh lint/types passed. The
final full foreground make check-all passed 4616 backend and 363 frontend tests,
with lint, strict types and coverage green.
