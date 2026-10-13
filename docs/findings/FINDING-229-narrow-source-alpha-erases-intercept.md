# FINDING-229: Narrow source alpha erases represented intercepts

- **Status:** Corrected (ADR-280)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 8, ISO 2026-W42
- **Decision:** ADR-280

## Finding and mechanism

Let native float32 or classic Float32 benchmark be .1 plus arange(3) times its
native spacing, and strategy be benchmark plus one spacing. Original values
have exact OLS beta1 and annual intercept 252*2**-27 = 1.8775463104248047e-6,
but the public comparator publishes beta1/alpha0. Native float16 at n4 publishes
alpha0 instead of .015380859375. Rounded source means erase the coefficient;
rounded beta also amplifies cancellation at large origins. No historical market
contamination is established. These are direct synthetic public reproductions.

ADR-279's excess moments correct a separate statistic and retain this limit.
Stable rounded means alone do not establish the unrounded OLS intercept contract
already adopted for integer sources by ADR-276.

## Correction and limits

ADR-280 selects only both-original native float16/float32 or classic Float32.
Encode exact original observations on the 2**-149 grid, accumulate exact Python
integer sufficient sums, and divide only the final annualized intercept. Preserve
published beta. Constants retain beta-zero convention with exact strategy mean
only; original guards remain first. Outside source families and excess/drawdown
stay. Narrow-family alpha rounding and some previously declined comparisons
change intentionally. No threshold, calibration identity or generated record
changes. Already-rounded subtraction, remaining beta precision and unsupported
source pairs remain separate; this is not whole-comparator precision certification.

## Verification

Independent pre-code scope approved 1,008 centered Fraction oracles, nine dtype
pairs n2–128 including full-width/tiny/large/constants, range bounds and .136s
100,000-observation streaming cost. Repository RED, final independent review,
full foreground gate and exact master CI are required for delivery.

Initial pre-code run had 235 failures/96 preserved, including 54 invalid positive
fixture assertions from half-ULP float16 offsets. Independent pre-code review
corrected the strategy offset to its own slope-scaled lattice without changing
any Fraction oracle. Added mixed-other-source bypass controls; the final unchanged-
production RED run observed 157 genuine failures and 204 preserved cases.
Focused new-alpha/prior-excess tests passed 469 cases after implementation.

Final independent research review approved the actual production helper against
1,008 centered Fraction oracles (504 also under strict NumPy state), 2,990 targeted
regressions, 819 exact complete outside-family HEAD comparisons, and 81 affected-
family comparisons with every other output exactly preserved. Input ownership,
metadata and error state passed. Whole-module AST restores exactly after removing
only the new helper, predicate and alpha branch; accepted integer helpers remain
unchanged. All 504 first-matrix public pairs are now accepted versus 406 before,
consistent with the intended exact-alpha availability change. Actual 100,000-row
helper took about .135 seconds.

The first full gate found six legacy constant-beta assertions expecting old rounded
float32/Float32 alpha (10,009 other cases passed). Only those narrow-family alpha
expectations now use independent exact Fraction means; beta-zero, ownership,
excess and all other dtype expectations remain. Published HEAD independently fails
all six strengthened cases while preserving nine controls. The updated constant/
alpha suites pass 382 cases and independent review approved the sixth path.
Fresh final foreground make check-all passed all 10,015 backend and 363 frontend
tests, with 97.70% backend and 97.63% frontend statement coverage. Lint, format
and strict typing passed. Exact master CI is verified after publication.
