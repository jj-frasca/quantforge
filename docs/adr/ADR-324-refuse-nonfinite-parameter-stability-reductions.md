# ADR-324: Refuse nonfinite parameter-stability reductions

- **Status:** Accepted
- **Date:** 2026-10-19
- **Deciders:** Codex autonomous session 3, ISO 2026-W43
- **Extends:** ADR-159/162/298/317
- **Resolves:** FINDING-274 for nonfinite native reductions

## Context

ADR-317 validates original observations and converted dimensionality, explicitly
leaving native arithmetic separate. Finite [1e155,2e155] gives mean1.5e155,
stdInf and stability_score0. ValidationReport accepts that finite zero despite
the unmeasurable internal dispersion. Finite [1e308,1e308] produces nonfinite
mean/dispersion/score and report validation refuses it. Under NumPy raise policy,
reductions already raise FloatingPointError. No production occurrence, false
graduate or calibration impact is established.

## Decision

Retain exactly the existing minimum-count, original-leaf and converted-shape
checks and all existing numerical statements. After the original mean and sample
STD statements, refuse a nonfinite mean or STD with ValueError. After the original
CV statement, refuse a nonfinite CV with ValueError. Retain the original return
expressions, epsilon1e-9, sample denominator, extrema, positive fraction and
clipped reciprocal. Native STD is nonnegative; finite CV and the positive epsilon
denominator imply the existing reciprocal is finite and bounded in [0,1].

Do not catch native exceptions, suppress warnings or set NumPy policy. Under
ignore/warn, nonfinite reductions now refuse before a dataclass is issued;
warn-mode reduction warnings still occur. Under raise, native FloatingPointError
can preempt the explicit ValueError and remains unchanged. Caller policy state
is never modified. This is a narrower successful arithmetic domain, including
previously accepted finite zero scores derived from infinite dispersion/CV.

No direct finite-STD/infinite-CV witness was established on the current reducer;
that guard defines supported finite coefficient evidence. An extended-real
CV=Inf has reciprocal limit0, but that limit does not establish a finite measured
coefficient. Do not claim every old zero was economically incorrect or every
exact answer must be recovered. Native underflow/zero dispersion, finite rounding
and Float64 projection remain separate. Do not add scaling, constant shortcuts,
variance recovery or a replacement estimator.

The dataclass/direct construction, report models, selector, all gate thresholds,
search identity, accounting-v14, generated records and frozen cohorts remain.
No accepted finite-intermediate statistic is repriced. Historical measurements
keep their executed attribution; no source/calibration rerun is authorized.

## Options considered

1. Refuse nonfinite native evidence while preserving every numerical expression.
   Chosen: narrow error boundary, analogous to ADR-298's arithmetic refusal.
2. Scale or translate all observations and recover overflow/underflow.
   Deferred: changes measured estimates and requires separate numerical and
   identity/calibration governance.
3. Keep score0 because it is finite and conservatively fails the gate.
   Rejected: a finite gate scalar cannot certify its missing internal statistic.
4. Normalize all native exceptions or suppress warnings.
   Rejected: unnecessary exception/policy compatibility change.

## Verification and reversal

Observe RED before runtime edits for actual report-accepted overflow witnesses,
mean overflow and signed/spread cases under ignore/warn. Verify native raise
exceptions/warnings and caller policy state, original validation precedence,
exact constants/zero, ordinary finite summaries and Hypothesis invariants.
Do not fabricate an observed finite-STD/CVInf case via mocks.

Twenty ordinary valid payloads are frozen in
/tmp/qf-w43-s3-stability-arithmetic-baseline.json, SHA256
7c82c5a4d9284ed4ab66d4a64aee058d3383eb79434a119579012c24c81fb6aa.
Require exact payload and whole prior AST preservation after removing only the
two finite guards and restoring the leading helper docstring. Independent final
research review, foreground make check-all, explicit paths, fresh fetch/rebase,
individual HEAD:master push and exact CI precede completion.

Reversal removes the two guards and restores the prior docstring, reopening
FINDING-274. Retain its evidence if reversing.
