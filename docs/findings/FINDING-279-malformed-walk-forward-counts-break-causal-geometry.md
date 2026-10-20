# FINDING-279: Malformed walk-forward counts break causal split geometry

- **Date:** 2026-10-20
- **Status:** Resolved by ADR-332
- **Scope:** walk_forward_splits original count arithmetic

## Evidence

walk_forward_splits(10,2,min_train=2.5) returns train/test overlap at row2 in
the first split and row5 in the second. np.float64(2.5) behaves identically:
fractional endpoint arithmetic and integer np.arange materialization disagree.
Parent and independent probes reproduce both cases. The unchanged ADR-197
evaluator rejects them with 'train rows must precede test rows'.

Independent bounded unsigned probes additionally confirm:

- (10,np.uint8(255),1): K+1 wraps and returns 255 folds, including empty tests.
- (np.uint8(250),2,np.uint8(200)): final-room arithmetic wraps; a test block
  includes rows200..282 outside its 250 observations.
- (10,2,np.uint8(255)): an impossible base wraps past the final-room guard and
  produces out-of-range rows.

The evaluator refuses every malformed case. A boolean K=True can also yield
one valid split and a finite diagnostic, showing missing original discrete
evidence validation without establishing a causal violation for that case.

## Impact and qualifications

This is an actual documented splitter-contract defect. It is not evidence of
accepted leaky scores, production corruption, affected graduates or changed
calibration rates. Normal default producers derive N from len and use native
integer counts; callers supplying unsupported count types expose these cases.
ADR-197 remains an independent evaluator boundary. Geometry checks do not
certify source provenance, strategy causality or self-financing switching.

## Resolution

ADR-332 validates original nonboolean Integral K/N/optional base before their
arithmetic, normalizing to Python int while preserving None and the original
formulas/check precedence. Parent froze 4,202 valid Python-int geometries,
including default/early/maximal starts and uneven remainder blocks, SHA256
9595b0ba9afa7a863b5043db3e39a2d7c6d06a418443f94a09c968b9f335a2d4.
Observed preimplementation RED: 33 failed/24 preserved controls before runtime
edits. Final new/original walk-forward suites: 95 passed. Independent five-path
review approved after rerunning 95 tests, 6,525 mixed typed legacy geometry
comparisons and whole prior module AST preservation. Parent preserved every
frozen payload and the prior AST except the helper import, two direct count
assignments, optional-base guard and splitter docstring. Foreground make
check-all passed 13,456 backend and 566 frontend tests, with lint, formatting
and types green. Runtime SHA256:
d79b287527fe185796afe79ebdff65eb9a7fb1ba7a107bd5ebec00ffff9a9d58.
No thresholds, generated data or frozen/historical cohort evidence change.
