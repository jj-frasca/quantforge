# FINDING-274: Overflowed stability dispersion publishes a finite zero

- **Date:** 2026-10-19
- **Severity:** Medium — invalid native arithmetic becomes a valid gate scalar
- **Status:** Resolved by ADR-324 for nonfinite native reductions/CV
- **Reviewed source:** 76f4c97d, parameter_stability.py
- **Related:** FINDING-268; ADR-159/162/298/317/324

## Evidence

Original observations can satisfy ADR-317 while their native reductions do not.
On NumPy2.5.4, parameter_stability([1e155,2e155]) returns mean_sharpe1.5e155,
std_sharpeInf, stability_score0 and otherwise finite fields. A real
ValidationReport accepts that zero as parameter_stability_score. The finite
scalar disguises unmeasurable dispersion rather than certifying the heuristic.

The separate [1e308,1e308] witness gives meanInf, stdInf and scoreNaN; the report
already rejects its NaN scalar. Native reduction overflow was noted but left
separate in FINDING-268. Both cases now get an explicit finite arithmetic domain.

Before correction, this reproduction prints the report-accepted zero:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import numpy as np
from app.validation.parameter_stability import parameter_stability
from app.validation.report import ValidationReport

with np.errstate(over='ignore', invalid='ignore'):
    result = parameter_stability([1e155, 2e155])
    print(result)
    report = ValidationReport(
        strategy_name='witness', observed_sharpe=1.0, deflated_sharpe=0.5,
        pbo=0.1, parameter_stability_score=result.stability_score,
        n_walk_forward_splits=0, n_purged_folds=0,
    )
    print('accepted stability', report.parameter_stability_score)
PY
```

Parent and required independent research review reproduce the same receipts:
/tmp/qf-w43-s3-stability-arithmetic-review.py/json and
/tmp/qf-w43-s3-stability-arithmetic-parent-review.json. Script SHA256:
6b388794ba25fa499fa677ef04c399725cbdb0f46fb2c7ba10cc4d833121e2ec.
The witnesses run under ignore/warn/raise and verify policy state is unchanged.
Ignore/warn issue summaries; warn emits native reduction warnings. Raise already
throws FloatingPointError. No search, RNG, provider or cohort execution is used.

## Scope and disposition

ADR-324 refuses nonfinite native mean/STD after those original reductions, then
nonfinite CV after its original expression. No native exception is caught and
no warning or NumPy policy is changed. Under ignore/warn, invalid evidence now
raises ValueError; under raise, native exceptions retain precedence. The
successful domain is intentionally narrower, including former finite zero
outputs derived from nonfinite intermediates.

No actual finite-STD/infinite-CV case was established on the current reducer.
The CV guard defines the supported finite-coefficient domain. Inf reciprocal0
is an extended-real limit; this finding does not claim all old zeros were wrong
or require numerical recovery of every representable theoretical answer.
Underflow, finite zero dispersion and finite projection/rounding remain separate.

Production callers compute their own Sharpe lists, and extremely large finite
scores are not ruled out by annotations or finite leaf checks. No actual
production occurrence, false graduate or historical-calibration impact is
established. This witness shows invalid measured evidence and potential refusal
changes, not threshold miscalibration or a reason to move a threshold.

Every original numerical statement remains: mean, sample STD, epsilon1e-9 CV,
extrema, profitable fraction and clipped reciprocal. No dataclass/model field,
heuristic, selector, threshold, search identity, accounting-v14, generated record
or frozen cohort changes. No accepted finite-intermediate estimate is repriced.
Direct ParameterStability construction and hostile conversion code are separate.

## Verification

Final actual preimplementation RED observed 12 failures and 10 preserved controls
in 2.79 seconds, with no production diff; initial 12/10 in 2.99 seconds is also
retained. Only test raw-regex literals and combined context-manager formatting
changed before the final RED. Log:
/tmp/qf-w43-s3-stability-arithmetic-red-final.log. All 72 focused tests, Ruff,
formatting and strict mypy pass. An initial focused invocation used an incorrect
legacy filename and stopped before tests; the corrected actual run passed.

Parent and independent preservation audits confirm all 20 frozen valid payloads
remain exact and the complete prior module AST matches after removing only the
two finite guards and restoring the leading helper docstring. Report and both
production caller source bytes are unchanged. Audit:
/tmp/qf-w43-s3-stability-arithmetic-audit.py/json. Independent final five-path
review approved and reran all 72 focused tests in 2.82 seconds. Final helper
SHA256: 46a1aa403640fa706682ba4d4a7808c21392d29cf7134af1acde7de2a43494b2.
Final test SHA256:
80315cb9030206202d37c6456f3fde93d5cb8769696b206f55c5a8bf87470617.

The first full gate passed 13,148 tests but failed an existing unrelated
paper-benchmark property on Hypothesis's timing deadline: 354.62ms initially
versus 8.22ms on replay at its original 200ms limit. No arithmetic assertion
failed. That unchanged property passed in isolation. No test, deadline, seed,
assertion or threshold was altered. A fresh foreground full gate with the
supported PYTEST_WORKERS=2 override passed 13,149 backend tests (97.40% coverage),
479 frontend tests (97.72% statements), lint, formatting and strict typing.
Both logs remain: /tmp/qf-w43-s3-check324.log and
/tmp/qf-w43-s3-check324-final.log. All local verification closed successfully;
exact master CI is verified after individual publication.
