# FINDING-213: Pairwise masking and ranking lose native IC order

- **Status:** Corrected — native IC inputs preserved before masking by ADR-264
- **Date:** 2026-10-12
- **Severity:** High for supported direct native diagnostic inputs
- **Scope:** Both average-rank inputs in cross-sectional rank_ic
- **Decision:** ADR-264

## Evidence

Homogeneous native int64 signals A=2**53+1, B=2**53, C=0 have three distinct
represented scores. Prices' next returns ordered A>B>C call for IC approximately
1. The final unscorable forward date inserts NaN during signals.where(scorable),
narrowing the integer frame to float64 before rank. A and B become a false average
tie; original rank_ic instead publishes approximately 0.866. Casting after masking
cannot recover this loss. Mixed integers and finite wide signals have analogous
failures; wide forward returns also require native ordering on their own side.

Independent research-expert reproduction confirmed all cases. A wide-price panel
can retain finite positive observations and finite native adjacent returns exceeding
float64 range; rank narrowing then fabricates return ties even with ordinary signals.
This is not ADR-261/262's supplied-first portfolio tie convention: IC requires average
ranks, so the correction must retain its own mathematical definition.
No historical cohort or production contamination is inferred. Canonical float64
production generators retain their exact original path and outputs.

## Correction and required evidence

Preserve native integer/wide scalars before masking both rank inputs. Keep the
existing pairwise missingness, true average ties, undefined-date dropping and
correlation/summary arithmetic. Independent pre-code review approved 1,000 exact
rational average-rank oracle cases under strict NumPy state, preserved caller inputs,
ordinary nullable/object/bool/float32 paths and all 16 generators/45 configurations.
No gate threshold, calibration identity, generated record, clipping, infinity
policy or summary-domain rule changes. Separate input-policy findings stay open.

## Observed verification

Initial RED included a NumPy-boolean test-oracle error; that oracle was corrected
before production edits. Final pre-implementation RED recorded 14 genuine failures
and 14 preserved cases. The helper correction passed 441 affected tests. Independent
final review approved 41 IC tests, 1,000 exact rational average-rank oracle panels
under strict NumPy state, 28 unchanged ordinary/alignment outcomes and exact full
IC series across 16 generators/45 configurations. Caller inputs/error state were
preserved; removing the helper and restoring both expressions matches the parent
source AST. Unsupported mixed complex inputs still raise, without a supported
finite-result claim.

Fresh foreground `make check-all PYTEST_WORKERS=4` passed: 5,344 backend
tests at 97.75% coverage and 363 frontend tests at 97.63% statement coverage;
lint, formatting and type checks passed.
