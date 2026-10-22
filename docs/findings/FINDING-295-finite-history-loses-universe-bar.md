# FINDING-295: Finite history can publish zero or infinite universe bars

- **Status:** Resolved under ADR-345
- **Date:** 2026-10-22
- **Severity:** Medium — unmeasurable derived evidence presented as an annotation
- **Reviewed revision:** `f618f220b58a1d1a4c0be6a4982e0a0d9dd19c7c`
- **Related:** ADR-018/344/345; FINDING-281/294

## Bounded evidence

With N607, the helper returns0 for finite native longdouble('1e400'), and
infinity for Python history2**-1074 or1e-320. Independent Decimal100/160/240
calculations from each original duration's exact integer ratio give positive
binary64-representable model answers:

| Original duration | Published bar | Decimal model, rounded for display |
|---|---:|---:|
| native longdouble('1e400') | 0 | 3.58009183990006e-200 |
| Python2**-1074 | infinity | 1.6106524564257913e162 |
| Python1e-320 | infinity | 3.5801117683206704e160 |

The native-wide reciprocal is positive but is lost when math.sqrt inspects it
as binary64. Tiny Python-history reciprocals overflow before the square root.
These are arithmetic representation failures, not impossible model answers.
Default-policy direct Python/wide witnesses emit no warning. Native NumPy tiny
durations can emit their original overflow warning or raise FloatingPointError.

This does not establish a production false graduate, corrupted record or changed
rate. A positive holdout Sharpe would trivially exceed an invalid zero bar, but
no actual graduate is constructed here. Existing producers normally derive
history/counts from validated records. ADR-344/F294 explicitly left this separate
finite-derived limitation untouched; their input refusal remains valid.

## Self-contained historical reproduction

Pin the reviewed source in memory, without checkout or repository mutation:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
import math
import subprocess
from decimal import Decimal, localcontext
import numpy as np
import app.research.lab.universe as module

revision='f618f220b58a1d1a4c0be6a4982e0a0d9dd19c7c'
source=subprocess.check_output(['git','show',revision+':backend/app/research/lab/universe.py'],text=True)
namespace=dict(vars(module))
exec(compile(source,'historical_universe.py','exec'),namespace)
bar=namespace['expected_max_sharpe_under_null']
for duration in (np.longdouble('1e400'),float.fromhex('0x0.0000000000001p-1022'),1e-320):
    with localcontext() as context:
        context.prec=160
        a,b=duration.as_integer_ratio()
        exact_duration=Decimal(a)/Decimal(b)
        oracle=(Decimal(2)*Decimal(607).ln()/exact_duration).sqrt()
        assert math.isfinite(float(oracle)) and float(oracle)>0
    value=bar(607,duration)
    assert value==0 or not math.isfinite(value)
    print(repr(duration),repr(value),str(oracle))
assert bar(51,0)==0
assert bar(607,np.longdouble(np.finfo(float).max)*2)>0
PY
```

No RNG, source generator, performance matrix, search, calibration, provider,
broker, credentials or network is used by these direct witnesses.

## Correction and limits

ADR-345 binds the unchanged product after the existing guards/shortcuts and
requires a finite positive final result. Unsupported arithmetic refuses rather
than publishing zero/infinity; accurate recovery remains deferred. Ordinary
finite results and native operations stay exact, including positive native-wide
2*float64max history and intentional N<2/T<=0 shortcut zeros.

Active NaN/infinite N can also produce invalid final evidence and now refuses;
this does not impose original integral/nonboolean N validation. Native operation
exceptions and warnings occur before the final check and remain uncaught.
No universal ValueError or finite-result accuracy guarantee follows. F281's
Gaussian annotation/model qualifications remain, as do all financial thresholds,
search/accounting identities and frozen/generated evidence. No rate inference
or cohort replay is authorized.

## Verification status

Independent prospective in-memory scope review approved the narrow refusal:
468 native compatibility controls and15 intended refusals across three NumPy
policies, preserving warning/error behavior and shortcut zeros. Independent
exact-native-ratio Decimal oracles agree with the parent at100/160/240 precision.

Session19 observed actual repository RED10 with27 passing controls before any
runtime edit. The first full gate found three existing NullCalibration tests
requiring the deflation_bar error identifier (14009 passed); the helper's new
message now includes that identifier, without changing any original test or
refusal logic. This failed gate is retained, not counted as green.

Final focused verification:291 passed, including all32 existing displayed-bar
tests. Independent research review approved the five paths, with184 initial
focused tests and69 after the message correction. Its broader native audit
preserved1120 outcomes and122 intended refusals across three NumPy policies,
including identical warning categories/messages. The complete prior module AST
matches except the declared leading docstring and exact final binding/check/
return; all1294 other tracked backend/frontend/data paths are byte-identical.
The pinned historical reproduction above passes. Default search/gate hashes
and accounting-v14 identity remain unchanged. Fresh foreground make check-all
passed14012 backend and570 frontend tests, with97.38%/97.83% coverage and
lint/format/type gates green. Publication and exact master CI follow this gate.
