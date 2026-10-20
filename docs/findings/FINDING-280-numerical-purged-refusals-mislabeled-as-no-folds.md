# FINDING-280: Numerical purged refusals are mislabeled as no folds

- **Date:** 2026-10-20
- **Status:** Resolved by ADR-333
- **Scope:** ValidationEngine's blanket purged-evaluator ValueError catch

## Actual synthetic witness

Use 300 UTC daily prices starting 2024-01-01, with close defined as
100*cumprod(1+default_rng(0).normal(.0002,.01,300)). Two causal synthetic
strategies emit exposure 1e-170 for the first ten observations and +1/-1
respectively afterward. Their parameter maps contain only the final exposure.
Run the real ValidationEngine with embargo230 and ordinary costs.

The generated first and last folds each have 10 training/60 test rows; only the
middle three folds are empty. The real BacktestEngine returns matrix gives the
unchanged purged evaluator's refusal 'nonconstant returns must have measurable
finite Sharpe moments': tiny initial nonconstant returns have zero native STD.
ValidationEngine instead catches that ValueError and publishes PCV=None with
'300 bars cannot hold 5 folds plus a 230-bar embargo'. The report JSON-roundtrips
and its passed field is False. Parent and independently implemented fresh probes
reproduce the same geometry, numerical cause and false explanation.

## Impact and qualification

This is an accepted report carrying the wrong absence explanation, not an
accepted numerical PCV score. No production occurrence, passing report, affected
graduate or changed calibration rate is established. Primary checks and the
standalone evaluator retain their guards; the enclosing catch loses the cause.

Longitudinal calibration calls search and this engine. Propagating these errors
changes affected inputs' completion/error classification and potentially the
completed denominator. Unchanged finite estimators do not establish unchanged
rates. Frozen/generated evidence must retain its executed historical meaning;
no replay, redraw or recalibration follows from this finding.

## Resolution

ADR-333 assigns genuine absence a ValueError subtype only at the existing final
no-fold check, after all original evidence validation and dropping. The engine
catches only that subtype, preserving genuine null/count0/flag outputs while
unrelated errors propagate. A preflight alternative was rejected because it
duplicates geometry inference and bypasses evaluator checks on the empty branch.
The existing class docstring's 'purged CV only counted' statement is also stale;
the measured diagnostic remains intentionally noncausal.

Parent froze 12 complete ordinary/genuine-no-fold report payloads, SHA256
55bee9f9e60d59e48bc59565530b4700ec0f7721662a1a5a54817f6a35539db1.
Observed preimplementation RED: 3 failed/7 preserved controls before either
runtime edit. Final new/evaluator/engine suites: 66 passed. Independent six-path
review approved after rerunning 66 tests, 870 empty-fold/source-validation
controls and both prior module AST comparisons. Parent preserved all 12 complete
reports and both prior ASTs outside the new class, final raise type, engine
import/catch/docstring. Foreground make check-all passed 13,466 backend and 566
frontend tests, with lint, formatting and types green. Runtime SHA256:

- purged_cv.py: e027ccd90bcdfe41e2647b0e0aac3915c669c6692b366f1f483b112ec00c7bf1
- engine.py: 27ab6c797a51c5c05124732113363240b21d42a0f9b62772ccb1a02180d73ca3

No threshold, finite score formula, generated record or frozen cohort changes.
