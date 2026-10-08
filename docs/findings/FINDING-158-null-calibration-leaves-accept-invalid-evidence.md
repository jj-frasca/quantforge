# FINDING-158: Null-calibration leaves accept invalid evidence

- **Date:** 2026-10-08
- **Severity:** High — malformed calibration evidence can alter interpretation
- **Status:** Resolved under ADR-213

## Reproduction

At `bb3ef2e0`, `NullGraduate(symbol="X", holdout_sharpe=NaN,
holdout_n_bars=0, deflated_sharpe=Infinity)` is accepted.
`NullSymbolDiagnostics(symbol="X", n_bars=0, holdout_years=-1,
walk_forward_oos_sharpe=Infinity, deflated_sharpe_probability=2)` is also
accepted. Boolean and numeric-string scores are coerced into apparent evidence.

Independent review constructs a legacy root containing a NaN graduate and
confirms that merge reconstruction accepts it: ADR-018 survival becomes false,
the maximum holdout statistic remains NaN, and JSON encodes the score as null.
Diagnostic percentiles and paired-excess consumers also trust these leaves.
No corrupted committed artifact or production false graduate is asserted.

ADR-158 defensively reconstructs calibration graphs, but reconstruction through
models lacking scalar guards cannot reject this evidence. The leaves need their
own intrinsic contracts, including standalone and JSON use.

## Correction and limits

ADR-213 rejects original nonreal/boolean/nonfinite scores, nonpositive or
noninteger history counts, nonpositive/nonfinite holdout years, and probabilities
outside [0, 1]. Valid signed/zero scores, numpy numeric scalars, and legacy absent
diagnostic/verdict fields remain supported. Nothing is dropped, clamped or
converted to an invented None.

Tests precede implementation and include unchecked-copy attachment and merge.
No data record, estimator, threshold, workflow or calibration identity changes.
Root legacy arrays/top-level scalar coherence, symbol identity and finite-score
subtraction overflow are separate boundaries; this leaf correction does not
claim complete calibration scalar safety.

TDD evidence: 58 failures and 14 preserved cases preceded implementation.
Independent final review found two exact-Fraction probabilities beyond [0, 1]
that rounded into the float interval; both failed before adding original-value
probability bounds. Initial 218 affected tests passed. Read-only compatibility
validated all eight committed null artifacts and 1,200 nested leaves. Final 220 affected and 74 standalone tests passed; strict typing, lint and
independent final research approval passed. Full foreground `make check-all
PYTEST_WORKERS=4` passed 3,237 backend and 359 frontend tests.
