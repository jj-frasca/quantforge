# FINDING-294: Infinite history publishes a zero universe annotation bar

- **Status:** Resolved — ADR-344 native nonfinite-history refusal
- **Date:** 2026-10-21
- **Severity:** Medium — invalid duration becomes a measured-looking annotation
- **Reviewed revision:** `77b9f5d16c974b3794e2210b49369bbdaa4b5d97`
- **Related:** ADR-018/292/296/334; FINDING-250/281/282

## Actual bounded evidence

At N607, expected_max_sharpe_under_null returns0 for +Inf supplied history,
NaN for NaN, and0 for -Inf. At N0 or1 it returns0 for all three through the
early selection-breadth shortcut. For comparison, T4 at N607 returns
1.79004591995003. A direct positive-score comparison against an invalid0 bar
would pass; this finding does not construct or infer an actual false graduate.

The tested legacy(51,0)->0 and ordinary finite negative-history shortcuts
are intentional compatibility. They are not selected for removal. F281 already
qualifies this leading-order Gaussian annotation's model limits; the present
issue is supplied-history validity, not another zero-error interpretation claim.

Current describe_frontier already refuses +Inf/NaN/-Inf via detectable_sharpe's
finite-positive duration guard. rank_experiments, pool-report near misses,
paper freezing and probability-DSR survival normally derive T from validated
positive holdout bars/252. Null/power leaf histories and complete null displayed
history relationships already enforce finite-positive evidence. No affected
production annotation, stored corruption, graduate or calibration rate is shown.
F250/ADR296 guards available graduation duration, and F282/ADR334 guards shared
Sharpe-SE inputs; neither repairs this standalone annotation helper.

## Self-contained historical-behavior reproduction

This pins the reviewed source in memory, without checkout or repository edits:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import subprocess
import numpy as np
import app.research.lab.universe as module
from app.research.lab.frontier import describe_frontier

revision='77b9f5d16c974b3794e2210b49369bbdaa4b5d97'
source=subprocess.check_output(['git','show',revision+':backend/app/research/lab/universe.py'],text=True)
namespace=dict(vars(module))
exec(compile(source,'historical_universe.py','exec'),namespace)
bar=namespace['expected_max_sharpe_under_null']
for n in (0,1,607):
    for t in (np.nan,np.inf,-np.inf,4.,0.,-4.):
        print(n,repr(t),bar(n,t))
assert bar(51,0)==0
wide=np.longdouble(np.finfo(float).max)*2
assert np.isfinite(wide)
print('finite wide',bar(607,wide))
print('finite huge native derived zero',bar(607,np.longdouble('1e400')))
print('finite huge negative integer shortcut',bar(607,-10**400))
for t in (np.nan,np.inf,-np.inf):
    try:
        describe_frontier(607,t)
    except ValueError as e:
        print('existing frontier refusal',repr(t),str(e))
    else:
        raise AssertionError('frontier must already refuse nonfinite history')
PY
```

Scratch actual-helper evidence: `/tmp/qf-w43-s15-universe-history-audit.py` and
`.json`; native predicate proposal audit:
`/tmp/qf-w43-s15-universe-native-history-audit.py` and `.json`.
Runtime Python3.12.13/NumPy2.5.4/pandas3.0.6. No source RNG, performance
matrix, search, calibration, provider, broker, credentials or network is used.

## Correction and compatibility

Before the unchanged branch, refuse original self-unequal history or exact
signed infinity with native comparisons, preserving all original operands.
No float inspection, positive-only history requirement, Real/nonboolean dtype
policy or N count policy is bundled. Invalid history now intentionally refuses
even when N<2 would formerly bypass it.

Independent scratch audit compares47 histories across N0/1/607. Native
Float16/32/64/longdouble NaN/infinity and0d nonfinite values refuse under the
implemented guard. Ordinary finite zero/negative, bool, Fraction, accepted0d numeric,
native finite wider values and huge negative integers retain results.
Native float128 T=2*float64max retains1.8880843389847055e-154. Native finite +1e400
retains the original derived zero, an uncorrected finite-arithmetic limitation
outside this original-nonfinite guard's scope;
negative1e400 and huge negative integers retain shortcut0. A math.isfinite
float-inspection guard would wrongly reject some of those genuine finite
controls, so it is not adopted by ADR-344.

Native comparison error behavior is not universal input validation: pd.NA,
multi-element arrays and Decimal sNaN may now fail earlier when N<2 formerly
skipped them. Do not normalize those errors or promise identical malformed-
input timing. Finite Decimal positive-history division errors and ordinary
unflagged scalar/native errors stay on their original path. Arbitrary custom
types, original count geometry and finite-derived overflow/underflow remain
separate. No stricter global scalar contract is inferred.

The corrected helper refuses invalid evidence rather than inventing a bar.
No affected historical rate or production occurrence is measured, and preserved
finite formulas do not prove unchanged rates or every caller's successful
completion. Keep annotation thresholds/model, fields, original N expressions,
gate/search fingerprints and intended accounting-v14 identity; changed source
provenance must be recorded separately. No frozen source/result replay,
regeneration, repair or relabeling follows.

## Verification status

ADR-344 was written before tests or runtime edits, following completed ADR-343
exact CI and fresh synchronization. Actual precode TDD: 73 refusal failures,
48 passing controls, and no universe-module source diff. After the exact native
guard, 157 focused tests passed, including 121 new cases with two Hypothesis
properties. Ruff, formatting and targeted mypy passed. Required independent
review reran 147 new/universe tests and approved all five paths.

Actual prior-HEAD versus implementation comparisons confirm expected refusals
and finite compatibility across 47 histories and three N branches, including native wide/0d, huge negative
integer, bool/Fraction and the legacy `(51, 0) -> 0` control. Receipt:
`/tmp/qf-w43-s15-universe-native-history-actual-audit.json`; independent receipt:
`/tmp/qf-w43-s15-universe-native-history-ACTUAL-final-review.json`.
Complete prior AST is identical except the exact guard and two declared doc
lines; original tests remain byte-identical. Search/gate fingerprints and
complete OpenAPI match the post-F292 parent. The pinned historical reproduction
passed independently. Session17's fresh independent review additionally passed
147 focused tests, 120 finite compatibility comparisons and 72 nonfinite
refusals; the exact embedded historical reproduction passed again.

Fresh session17 foreground `make check-all PYTEST_WORKERS=2` passed: 13,975
backend tests, 570 frontend tests, 97.38% backend coverage and 97.83% frontend
statement coverage, with lint, formatting and strict type checks green.
Receipt: `/tmp/qf-w43-s17-check344.log`. Exact master CI is verified after publication.

Qualified universe source SHA256: `46819c2268d9e45b6800d13a3be648bd1d08577dd7bb416dc37ae598f05c91d0`;
other 1,293 tracked backend/frontend/data paths remain byte-identical. Receipt:
`/tmp/qf-w43-s15-universe-history-ast-audit.json`.
