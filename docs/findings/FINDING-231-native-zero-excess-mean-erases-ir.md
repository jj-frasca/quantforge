# FINDING-231: Zero native excess means erase represented information ratio

- **Status:** Corrected (ADR-282)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 8, ISO 2026-W42
- **Decision:** ADR-282
- **Prior art:** ADR-209's foundation Sharpe zero-evidence contract

## Finding

Native float64/classic Float64 strategy [0,1e-100,2] versus benchmark [2,0,0]
produces excess [-2,1e-100,2], IR0 and TE31.74901573277509. Native std2 has no
underflow; original fsum retains1e-100. Against the intentionally preserved
native std, the independent Fraction ratio is approximately 2.6457513110645907e-100.
The initial smallest-subnormal candidate was dismissed by actual post-ADR281
reproduction: ADR-281 already detects its squaring underflow and publishes correct
IR1.5e-323. This finding concerns only remaining native-zero means with measurable
native dispersion. No historical market contamination is established.

## Correction and limits

ADR-282 certifies zero using original fsum only for nonconstant native/masked
float64 excess with positive finite native dispersion and no ADR-281 recovery.
True zero remains zero; a nonzero sum feeds an annualized ratio through separated
exponents, retaining the existing measured std. Uncertified overflow refuses.
TE is unchanged exactly, as are nonzero native mean paths, other excess families,
constants, ADR-281 recovery and every source/non-risk output. No threshold,
calibration identity, schema, workflow or generated record changes.

The ratio contract deliberately uses existing native std, not an invented exact
variance. Normal oracle comparisons use 1e-12 relative precision; subnormal
comparisons retain sign/nonzero evidence and a one-output-ULP bound. This is no
universal correctly rounded ratio or nonzero-native-mean accuracy guarantee.
Source log1p strict-state limits remain separate.

## Verification

Independent pre-code scope approved 360 exact Fraction-total/native-std cases,
300 complete outside comparisons and 36 extreme-range subnormal cases. Draft 61
prototype tests passed. Added explicit zero-mean other-family bypasses and original
source guards before production. Repository RED observed 53 genuine failures and
20 preserved cases; two context-manager style fixes preserved all assertions.
Focused new/prior tests passed 627 cases after implementation.

Final independent review approved 360 production Fraction-sum/known-std public
cases, 36 extreme/subnormal cases, 227 targeted regressions and 300 exact complete
unaffected HEAD comparisons with strict state and input ownership. All 360
changed cases preserve every non-IR output exactly. Whole-module AST restores
by removing only the helper, predicate alias and eligible mean/IR dispatch;
ADR-281 and every other helper remain unchanged, including native wider mean
precision. True original zero sums retain conventional zero.
The first full gate stopped on strict typing of the shared float/wider std
variable; the float64-only call now makes its already-Python-float operand
explicit. Wider paths bypass this cast; all 396 oracles and 300 preservation
comparisons were repeated successfully after it. Fresh foreground make check-all
passed 10,152 backend and 363 frontend tests, 97.67%/97.63% coverage, with lint,
format and strict typing green. Exact master CI is verified after publication.
