# FINDING-222: Unsigned excess subtraction reverses return evidence

- **Status:** Corrected (ADR-273)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-273

## Finding and mechanism

Unsigned [0,1,2]-[1,2,3] should produce [-1,-1,-1]. Original uint8/16/32/64
and UInt8/16/32/64 pairings instead wrap to positive maximum values. All source
numeric/calendar/finite/>-1 guards pass; the published excess is false but finite.

For [0,3,2]-[1,2,4], exact signed differences [-1,1,-2] have mean -2/3,
sample variance 7/3, annualized information ratio -6.928203230275509.
uint8 publishes [255,1,254] and IR +18.438658512080796; uint64 gives positive
maximum values and IR +18.33030277982336. Beta, alpha and drawdown retain their
own source computations; no historical market contamination is established.

Converting both operands first is inadequate: at 53-bit precision maxuint64 and
maxuint64-1 collapse together although their difference one is exactly encodable.
Conversely maxuint64 minus zero is not exactly encodable on those platforms and
must be refused, not rounded into valid-looking evidence.

## Correction and limits

ADR-273 selects only both-original-unsigned native/classic masked sources,
subtracts original scalars as Python integers, then certifies native floating
encoding of each difference with exact integer ratios. Original aligned index
and public pandas name consensus remain. Other subtraction paths, beta/alpha,
drawdown and guards retain their original code; corrected IR/TE naturally change.
ADR-272 prevents the signed native representation from fabricating constant risk.

This is not certification of large original integer means/covariance, mixed
signed source precision, other moments, source float64 validation or final scalar
rounding. No threshold, calibration identity or generated record changes.

## Verification

Independent pre-code prototype passed 256 all8x8 pairing/fixture cases, exact
Python difference/Fraction/Decimal dispersion oracles, large neighbor difference
one, and constrained53bit +/-max refusal. Public regressions observed 284 genuine
failures and 37 preserved controls before production changes. Only afterward
was the reviewed exact helper and both-unsigned dispatch implemented.

All 508 affected benchmark/API tests pass. Three raw-regex lint strings were
corrected without changing assertions. Final independent research-expert review
approved 321 unsigned/dispersion tests, 256 public all8x8 pairing/fixture probes
with independent Python-int signed excess and Fraction/Decimal IR/TE, source
ownership and strict caller state, native max/neighbor controls and constrained
53-bit encoding refusal. Ninety complete ordinary/nullable/native-wide outputs
match the current pre-code HEAD exactly, including excess dtype/name/index.
Removing only the helper, unsigned dtype declaration and dispatch restores the
complete baseline module AST. Existing ADR-272 unsigned maximum expectations now
require exact representability across platforms; the original native floating
represented-constant control remains. No tests were deleted or skipped.
Full foreground `make check-all PYTEST_WORKERS=4` passed: 5,985 backend tests,
97.72% coverage; 363 frontend tests, 97.63% statement coverage. All verification
completed before commit. No generated records, thresholds or calibration changed.
