# FINDING-223: Mixed integer promotion erases signed excess evidence

- **Status:** Corrected (ADR-274)
- **Date:** 2026-10-13
- **Review:** Codex autonomous session 6, ISO 2026-W42
- **Decision:** ADR-274

## Finding and mechanism

At base=int64max-4, strategy integer offsets [0,3,2] versus benchmark [1,2,4]
have exact signed differences [-1,1,-2]. Mixed plain/masked uint64 and int64
source pairs publish float64 zeros because pandas rounds original operands before
subtraction. Four representation pairings and reverse sides reproduce eight
public failures after the separate both-unsigned ADR-273 correction.

IR and tracking error publish zero instead of Fraction mean -2/3, sample variance
7/3 and annualized IR -6.928203230275509 (opposite sign in reverse). All original
source guards pass. No historical market contamination is established. This is
not the modular wrap of FINDING-222 and not repaired by its both-unsigned scope.

## Correction and limits

ADR-274 additionally dispatches original mixed signed/unsigned native/classic
masked integer families through exact Python differences before certified native
encoding. Index/name consensus and original source guards remain. This family
policy deliberately changes every mixed integer excess dtype to plain native
floating, including smaller pairs that subtracted correctly; IR/TE may change
through ADR-272. No byte-exact promise for mixed-pair complete results is made.

Other branches, including both-unsigned ADR-273, signed-only and floating/native
wide comparisons remain; beta/alpha/source moments and drawdown keep their code.
Large integer source moments, float64 source validation, native arithmetic and
final scalar rounding remain separate limits. No threshold, calibration identity
or generated record changes.

## Verification

Independent scratch approved eight public large-neighbor counterexamples, 512
all8x8/both-direction/four-fixture exact cases and 128 original-negative guard
probes. Public tests observed 541 genuine failures and 292 preserved controls
before production. A context-manager lint correction preceded RED without changing
assertions. Only afterward was the narrow family predicate/dispatch implemented.

All 1,055 affected benchmark/API tests pass. The equivalent combined isinstance
tuple corrected a lint rule before the full gate. Final independent research-expert
review approved 833 mixed/unsigned tests, 512 public all8x8/both-direction cases
with independent Python-int/Fraction/Decimal oracles, strict caller state and
source ownership, eight large-neighbor corrections and 128 source-negative guard
probes. Native max encoding and inherited constrained53bit certification pass.
Ninety complete ordinary/signed-only/nullable/native-wide outputs and 64 complete
both-unsigned outputs match pre-code HEAD exactly. Removing only the new dtype
declaration, predicate, dispatch and helper purpose docstring restores the full
baseline module AST. Metadata/partial overlap/missing refusal are preserved.
Full foreground `make check-all PYTEST_WORKERS=4` passed: 6,532 backend tests,
97.72% coverage; 363 frontend tests, 97.63% statement coverage. All verification
completed before commit. No generated records, thresholds or calibration changed.
