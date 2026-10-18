# FINDING-226: Masked Float32 beta mixes two moment precisions

- **Status:** Resolved by ADR-277; preserved by ADR-278 low-width extension
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-277

## Original finding and mechanism

Classic masked Float32 .1 and its next two native ULP neighbors compared against itself
publishes beta0.4 and annual alpha15.120002746582031 instead of beta1/alpha0.
Plain float32/float16 controls retain neutrality. Original values are finite,
real, wealth-preserving and nonconstant. Installed masked variance delegates
np.var over float32 arrays; Series.cov already extracts float64 arrays. The
positive native denominator is biased at different precision, with no underflow
to invoke existing recovery. No historical market contamination is established.

## Correction and limits

ADR-277 matches native sample variance to that existing covariance precision only
for classic masked Float32 benchmarks, after integer/wider/constant precedence.
Existing underflow recovery uses matched plain float64 normalized operands for
that branch; otherwise the original masked denominator can repeat the defect.
Every other benchmark path, source guards, original covariance/scale restoration,
means, excess/IR/TE/drawdown and metadata remain. Alpha naturally changes with beta.

This does not certify source float32 means or dispersion, large integer partner
precision, float64 centering, uneven normalization or whole-comparator strict
error state. No threshold, calibration identity or generated record changes.

## Verification

Independent pre-code scratch: 420 Fraction beta probes across 21 partner types,
n3–128/origins .1/.5/1/-.1, tiny strategies and subnormal benchmark recovery.
Installed pandas source confirms mismatch; temporary public prototype passed all
446 proposed tests. Unchanged repository RED then observed 398 genuine failures
and 48 preserved controls before the two narrow moment conditionals were implemented.

All 3,213 affected benchmark/API tests pass. Final independent research-expert
review approved 446 public Fraction/self/property/recovery tests. Three hundred
forty-eight complete ordinary/integer/nullable Float64/native-wide outputs,
including wider strategy plus Float32 benchmark, exactly match pre-code HEAD.
Excess, IR, tracking error and drawdown stay exact across all 420 affected cases;
beta/alpha changes are intentional. Removing only the denominator/recovery
conditionals restores the complete baseline AST, with covariance unchanged.
Constant precedence, source guards/state/ownership/overlap and subnormal recovery
pass; no whole-comparator strict-state claim is made. Full foreground
`make check-all PYTEST_WORKERS=4` passed: 8,690 backend tests, 97.71% coverage;
363 frontend tests, 97.63% statement coverage. All verification completed before
commit. No generated records, thresholds or calibration changed.

## Status reconciliation — 2026-10-18

The Open header contradicted this report's implemented correction and recorded
verification, and ADR-277's explicit Resolves designation (`7392bdde`). ADR-278
extends the matched-precision branch to native low-width benchmarks without
reversing the masked Float32 correction.

Parent replay of the original Float32 .1/next-two-ULP self-comparison returns
beta 1 and annual alpha 0, retaining the Float32 source type. Receipt:
`/tmp/qf-w42-s30-f226-parent.json`. Independent research replay under strict NumPy
policy returned the same values, preserved the input and emitted no public-call
warnings. The superseded raw covariance/native-variance ratio still gives 0.4,
confirming the original mechanism without identifying a remaining public defect.
Review: `/tmp/qf-w42-s30-stale-finding-review.md`.

This closure covers the documented moment-precision mismatch only. It does not
certify arbitrary centering/cancellation, source representation, partner
compatibility, alpha/excess precision or whole-comparator strict-state behavior.
The status correction changes no implementation, threshold, generated record or
historical market-impact claim. Full verification is recorded below.

Independent final review approved this documentation-only reconciliation. Fresh
full foreground `make check-all PYTEST_WORKERS=4` passed 12,787 backend tests
(97.39% coverage) and 438 frontend tests (97.69% statements), with lint, formatting
and strict types green. Receipt: `/tmp/qf-w42-s30-check-status.log`. Only these two
finding documents change; production, frontend, tests and generated records stay
byte-identical. Exact master CI is verified after individual publication.
