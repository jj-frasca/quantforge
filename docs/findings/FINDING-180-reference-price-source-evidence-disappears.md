# FINDING-180: Invalid reference prices can become finite effect-size evidence

- **Date:** 2026-10-09
- **Severity:** Medium — malformed source evidence can produce a reference score
- **Status:** Corrected by ADR-230
- **Affected:** oracle_sharpe_of and historical/explicit-drift AR wrappers

## Reproduction

At revision 0131288c, closes [100, 101, NaN, 100, 101] produce 0.0 through
all three entries: pct_change/dropna reduces the measured history before the
legitimate short-history shortcut. A singleton NaN also returns zero. Missing
prices are not measured zero returns or an honest short complete history.

Closes [-100, -101, -100, -101, -100] produce historical and explicit-drift
AR scores 23.81071058888849 (phi=-0.3, drift=0, cost=0), despite violating
the positive-price contract. Complex closes [1+1j, 2+1j, 1+1j, 2+1j, 1+1j]
produce finite scores while emitting ComplexWarning for discarded imaginary
parts. The generic constant-positive-mean score is 1.2057554287027517.
These are deterministic malformed direct calls, not observed corrupt generated
artifacts, new draws, search outcomes or evidence against the gate's calibration.

## Correction boundary

Validate original real nonboolean numeric, finite positive close observations
before return construction at each reference entry. Preserve original native
valid-price arithmetic and conditional-mean missing startup. No source filling,
dropping, coercion, reference replacement, threshold/fingerprint change or data
write. Calendar ordering, original generic cost/mean policy and extreme finite
numerical precision remain separate questions.

## Verification

TDD observed 76 failures and 27 preserved cases before the helper was added.
All 171 targeted cases passed. Independent final review approved all five
paths with 314 relevant tests and 14 exact native AR/band producer comparisons.
The shared helper preserves original Series arithmetic and the previous
conditional-mean startup behavior. Full foreground `make check-all PYTEST_WORKERS=8` passed: 3,976 backend
and 363 frontend tests, with lint, typing and coverage green.
