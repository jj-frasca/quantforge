# FINDING-277: Unsigned purged split counts overlap their own test rows

- **Date:** 2026-10-20
- **Status:** Resolved by ADR-330
- **Scope:** standalone purged_kfold_splits original count arithmetic

## Evidence

Before runtime edits, both parent historical probes and a fresh independent
research review confirm purged_kfold_splits(8,2,np.uint32(2)) and uint64(2)
return first-fold training rows0..7, including test rows0..3. Native unsigned
start-embargo wraps rather than becoming -2. Separately, unsigned N8 or K2
with Python embargo10 contaminates size/start arithmetic and returns second-fold
training rows0..7, including its own test rows4..7. Python-int controls purge
those rows. The supplied embargo is not the geometry actually returned.

Minimal reproduction (run from backend with its environment):

```python
import numpy as np
from app.validation.purged_cv import purged_kfold_splits

for args in [(8, 2, np.uint64(2)), (np.uint8(8), 2, 10),
             (8, np.uint8(2), 10)]:
    folds = purged_kfold_splits(*args)
    print([np.intersect1d(train, test).tolist() for train, test in folds])
```

Pre-fix outputs respectively contain [0,1,2,3] in the first fold and [4,5,6,7]
in the second fold for each remaining request. Invalid coercible/nonintegral
counts also lack a consistent original-evidence boundary.

## Impact and mitigation

This is an actual splitter embargo-contract failure, not evidence of accepted
leaky scores. The unchanged ADR-198 evaluator rejects every witnessed overlapping
fold with 'train rows violate the declared embargo'. ValidationEngine catches
that refusal as unmeasured PCV, with a too-short-history flag that can misdescribe
this cause. ADR-325's normal panel producer validates/normalizes requested folds
and floor upstream; its observation count is native int. No affected production
record, false graduate or changed calibration rate is established.

## Resolution and verification

ADR-330 normalizes the three original discrete counts before their existing
checks and all geometry. Exact Python-int requests, evaluator safeguards and
all scientific formulas remain. The separate NumPy parameter omission in
lookback_embargo and general engine error attribution are outside this fix.

Observed preimplementation RED: 49 failed/20 preserved controls before any
runtime diff. Final new/original purged suites: 113 passed. Independent review
approved all five paths, reran 113 cases and checked 9,936 mixed typed requests
against a separate exact set oracle under NumPy raise policy. Parent comparison
preserved all 5,460 frozen Python geometry payloads (SHA256
bb72622f37c4a46af8b854fca5636888313ad930d37b705fc1ce32b5c57fc1e9)
and the complete prior module AST except the helper import, three assignments
and leading splitter docstring. Foreground make check-all passed 13,372 backend
and 566 frontend tests with lint, formatting and types green. Runtime SHA256:
fa516a8c71bc6581cf31004c29e1a0c5c552ef0bf5172cc5a43aa2d42e0a891d.
