# FINDING-224: Integer beta erases source differences and invents same-series alpha

- **Status:** Corrected (ADR-275)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-275

## Finding and mechanism

base=int64max-4 and returns[base,base+1,base+2] are exactly distinct original
int64/Int64/uint64/UInt64 observations. Comparing each Series against ITSELF
publishes beta0 and annual alpha 2.3242897532874035e21 instead of beta1/alpha0.
Pandas float64 moments erase the original integer variation, and scaled recovery
sees the same fabricated constant in its float64 arrays. Exact source equality
correctly recognizes nonconstant originals; native wider beta excludes integers.
No historical market contamination is established. Excess corrections are separate.

## Correction and limits

ADR-275 chooses exact Python integer covariance sufficient sums only for supported
both-original-integer sources after exact constant/validation guards. Own-first
translation and streaming sums retain exact numerator/denominator before one final
integer quotient to float. This deliberately changes the integer-family beta path;
all noninteger paths and original mean/alpha, excess/IR/TE/drawdown operations stay.
Alpha naturally changes with beta. Original means and other statistic precision
remain explicit limitations; no threshold/calibration identity/record changes.

The initially considered translated native moment approach was rejected before
ADR/code: besides unnecessary encoding refusals, it leaves beta4.07e-20 for exact
zero covariance in a full-width integer fixture. Exact sufficient sums give zero
without native encoding or Fraction objects in production. This is no blanket
whole-comparator precision or strict-state guarantee.

## Verification

Independent exact-sum scratch: 540 Fraction covariance-ratio oracles with n2–128,
full uint64, large origins/neighbors, uneven cancellation; 100k-row cost0.046s.
Initial public RED observed 311 failures/558 preserved: 55 large-value/alignment/
property failures plus 256 small-integer cases deliberately requiring exact final
beta0.5 instead of native0.5000000000000001. Before production, independent review
made the public zero-covariance fixture capability-aware to preserve existing
exact excess encoding, and added a direct full-width helper oracle on every
platform. Final unchanged-source RED observed 312 failures/558 preserved controls.
Only afterward was the exact helper/predicate/beta dispatch implemented.

All 1,925 affected benchmark/API tests pass. Final independent research-expert
review approved 870 new tests, 540 production-helper Fraction covariance-ratio
oracles across n2–128/full-width/uneven cancellation and exact-zero covariance.
Seventy complete ordinary/nullable/native-wide and 32 mixed integer/float outputs
remain exactly equal to pre-code HEAD; excess, IR, tracking error and drawdown are
unchanged across 256 integer pairs (beta/alpha intentionally excluded).
Removing only the helper, integer predicate and beta dispatch restores the full
baseline module AST. Constants and original source guards remain first; the
integer branch cannot enter float64 scaled recovery. State/input/alignment and
valid property bounds are verified. Full foreground `make check-all
PYTEST_WORKERS=4` passed: 7,402 backend tests, 97.71% coverage; 363 frontend
tests, 97.63% statement coverage. All verification completed before commit.
No generated records, thresholds or calibration changed.
