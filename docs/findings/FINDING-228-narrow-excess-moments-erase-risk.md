# FINDING-228: Narrow excess moments erase represented risk

- **Status:** Corrected (ADR-279)
- **Date:** 2026-10-13
- **Review:** Codex autonomous sessions 6 and 8, ISO 2026-W42
- **Decision:** ADR-279

## Finding and mechanism

Native float16 [1e-6,2e-6,3e-6], native float32 or classic masked Float32
[1e-24,2e-24,3e-24], each versus same-dtype zero benchmark, publish IR0/TE0.
Original excess is nonconstant but narrow sample variance underflows before
sqrt. Float32 [1e30,2e30,3e30] instead declines on infinite tracking error though
its original sample standard deviation is float64 measurable and alpha finite.
No historical market contamination is established.

A variance-only promotion would introduce another false claim: original sources
[A,tiny,0] versus [0,0,A] have excess [A,tiny,-A]. For float16 A256/tiny1e-6 or
float32 A1e20/tiny1e-24, narrow summation loses a positive mean; the float32
examples lose it even after ordinary float64 promotion. Wider dispersion newly
becomes measurable. Both wider dispersion and stable
fsum mean are needed. ADR-278 source beta repair was separately delivered first.

## Correction and limits

ADR-279 selects only native float16/32 or classic masked Float32 excess after
exact constant detection. Temporary float64 sample std(ddof1) and fsum mean
retain represented risk and cancellation evidence in the original formulas.
Original Series, source guards/beta/alpha/drawdown and other excess types stay.
No epsilon, validation threshold, calibration identity or generated record changes.
This does not repair rounded subtraction, source alpha, or masked-byte-integer
compatibility and makes no universal precision/whole-comparator availability claim.

## Verification

Independent pre-code scope review approved 83 public Fraction/Decimal moment
oracles, three source cancellation cases and explicit float64 range bounds.
Inherited repository TDD log confirms 87 genuine failures and 21 preserved cases
before production edits. Fresh independent session8 review approved all five paths:
108 new tests, 4,067 existing regression tests, 81 public Fraction/180-digit Decimal
probes, and 147 complete unaffected HEAD-baseline results exactly preserved,
including excess metadata, input ownership and strict NumPy state. Four extreme
float16 probes retain the documented unchanged source-alpha overflow refusal.
Fresh session8 foreground make check-all passed 9,654 backend and 363 frontend
tests, with 97.71% backend and 97.63% frontend statement coverage; lint, format
and strict typing passed. Exact master CI is verified after publication.
