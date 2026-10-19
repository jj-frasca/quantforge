# FINDING-273: Invalid market prices fabricate bull-regime evidence

- **Date:** 2026-10-19
- **Severity:** Medium — malformed descriptive evidence at a public helper
- **Status:** Resolved by ADR-323 for the supported matched-market domain
- **Reviewed source:** b3bbd171, validation/regime_analysis.py::analyze_regimes
- **Related:** ADR-012/178/318/319/320/323

## Reproduced evidence

With strategy returns [0.01,-0.02,0.03] repeated eight times and the same ordered
24-row calendar, each of these market series returns identical finite evidence
under the public helper's default window20: all NaN, all zero, or all True.
All are labeled bull24, total_return0.16701756688183367,
Sharpe5.041929455236252. A real ValidationReport accepts each regime dictionary.
This witness does not rely on unchecked model construction or a mock.

Before the correction, this repository-root reproduction prints the fabricated
bull result for all three inputs. After correction it must refuse each:

```sh
PYTHONPATH=backend backend/.venv/bin/python - <<'PY'
from dataclasses import asdict
import numpy as np
import pandas as pd
from app.validation.regime_analysis import analyze_regimes
from app.validation.report import ValidationReport

returns = pd.Series([0.01, -0.02, 0.03] * 8)
for invalid in (np.nan, 0.0, True):
    raw = analyze_regimes(returns, pd.Series(invalid, index=returns.index))
    report = ValidationReport(
        strategy_name='witness', observed_sharpe=1.0, deflated_sharpe=0.5,
        pbo=0.1, parameter_stability_score=0.5,
        n_walk_forward_splits=0, n_purged_folds=0,
        regime_breakdown={label: asdict(metrics) for label, metrics in raw.items()},
    )
    print(report.model_dump(mode='json')['regime_breakdown'])
PY
```

Missing market pct_change comparisons do not satisfy trailing<0, so the initial
bull label survives. Without price validation, genuine warmup and invalid
mature observations are indistinguishable. Nonpositive and boolean prices also
lack the economic interpretation claimed by a market trailing return. Parent
and required independent research-expert witnesses match on pandas3.0.6 and
NumPy2.5.4. Richer scratch witness, including current normal-engine refusals:
/tmp/qf-w43-s3-regime-market-review.py; parent output:
/tmp/qf-w43-s3-regime-market-parent.log. No search or calibration was run.

## Scope and correction

Current normal ValidationEngine computes its strategy paths on data.close before
regime assembly. BacktestEngine already refuses the demonstrated malformed
prices, mitigating that route. No production occurrence, false graduation,
future-information leakage or historical-calibration impact is established.
Regime partitions are retrospective descriptive diagnostics, not executable
switching accounts or a graduation threshold.

ADR-323 validates nonempty matched market dtype and native positive finite
values before pct_change, after the existing window/calendar/wealth guards.
Missing values are refused rather than assigned another invented regime.
Object dtype is intentionally unsupported, including Decimal/numeric strings.
Native and nullable complete real numeric prices remain supported without
Float64 narrowing. Empty/disjoint results remain empty; unmatched invalid
numeric observations remain unscored. Object dtype remains unsupported even
if its matched leaves are numeric. Genuine valid-price warmup and zero-horizon
bull labels retain their meaning. Derived trailing-return arithmetic limits,
source provenance, cadence, original-source completeness and native aggregate
precision remain separate.

No scoring formula, report schema, threshold, selector, accounting-v14, generated
record or frozen cohort changes. Twenty-four prechange valid payloads and full
prior AST preservation bound behavior compatibility; they are not universal
numerical or provenance certification.

## Verification

Actual preimplementation RED observed 28 failures and 14 preserved controls in
5.95 seconds, with the production helper diff empty. Log:
/tmp/qf-w43-s3-regime-market-red.log. After the narrow guard, 133 focused tests
passed; the final 42 new cases pass after test-only raw-regex literal and
equivalent property assertion formatting. Ruff/format and strict mypy pass.

Parent and independent review both confirm all 24 frozen valid payloads remain
exact and the complete prior AST is preserved after removing only the added
imports/guard and restoring the helper's leading docstring. Audit:
/tmp/qf-w43-s3-regime-market-audit.py/json. Independent final five-path research
review approved and reran 139 focused tests in 5.35 seconds. Report models and
both engine modules remain byte-unchanged. Final helper SHA256:
ef64a73ae9e535cceaabc476fc45cb1bbbd072c174fdda8b213b8650b3247e33.
Final test SHA256:
319cdf5915061a41f828cd5bdf8091fe6795e28fd3e99ff015bd053b82c3b6d4.

Fresh foreground make check-all PYTEST_WORKERS=4 passed 13,127 backend tests
(97.41% coverage), 479 frontend tests (97.72% statements), lint, formatting and
strict types. Log: /tmp/qf-w43-s3-check323.log. All local checks closed
successfully; exact master CI is verified after individual publication.
