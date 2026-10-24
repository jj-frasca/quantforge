# FINDING-296: Lifecycle drawdown omits forward inception

- **Date:** 2026-10-24
- **Status:** Resolved by ADR-356
- **Area:** Single-name and cross-sectional forward lifecycle risk

## Evidence

At revision `8549c3fe`, both lifecycle routines compound forward returns and
pass the post-return equity to max_drawdown without a pre-return unit baseline.
The first loss becomes the first peak; subsequent recovery cannot reveal it.
This repeats the accounting mechanism corrected for BacktestMetrics by ADR-110
and for benchmark-relative drawdown by ADR-112, in separate lifecycle consumers.

Deterministic reproduction (no provider, broker, search or RNG):

```python
import pandas as pd
from app.research.lab.paper import ExitPolicy, lifecycle_from_returns
from app.research.cross_sectional.forward import (
    CrossSectionalExitPolicy, lifecycle_from_forward_returns,
)

returns = pd.Series([-.35] + [.009, .011] * 50)
benchmark = pd.Series(0., index=returns.index)
single = lifecycle_from_returns(returns, benchmark, ExitPolicy(), 1)
panel = lifecycle_from_forward_returns(returns, benchmark, CrossSectionalExitPolicy())
assert single.action == panel.action == "hold"
assert single.forward_drawdown == panel.forward_drawdown == 0.
assert single.reasons == panel.reasons == []
```

The first post-return wealth is 0.65; all later wealth increases. Relative to
the actual pre-return unit baseline, maximum drawdown is 35%. This exceeds the
unchanged default single-name 25% and panel 30% risk limits. Rolling Sharpe uses
the last 63 positive alternating observations and exceeds its default floor;
the flat benchmark does not trigger an exit. Thus the missing risk reason can
change the actual lifecycle action, without relaxing a threshold.

## Scope and correction

ADR-356 adds a same-dtype unit baseline only after the existing grace/no-trade
branches and existing native cumprod. Original observations, rolling statistics,
limits, strict comparisons, reason text, schemas and policy hashes remain.
This concerns normalized strategy/factor forward wealth, not observed broker
account equity. No actual production occurrence, affected position, order or
false graduate is established; generated records remain unchanged. Historical
cohorts and calibration attribution are untouched. Extreme compounding and raw
max_drawdown source validation remain separate limitations.

## Verification

Independent research review reproduced the default-policy witness before source
edits. Actual preimplementation tests produced 24 failures and 14 passing controls
in 3.50s (`/tmp/qf-w43-s26-lifecycle-red.log`). After the narrow patch, 306 focused
lifecycle/identity tests passed in 7.04s, including 38 new cases and bounded
Hypothesis tests against exact Fraction complete-wealth paths. Tests preserve
strict risk-limit equality, grace/no-trade branches and original Series/dtypes.

Independent final research review approved all six paths and separately ran the
38 new tests. Parent and reviewer AST checks found both whole prior modules
identical after removing only their new baseline assignment. Parent compatibility
checks retained 96 exact nonloss-first decisions and the other rolling statistics
across 160 native/nullable cases (`/tmp/qf-w43-s26-lifecycle-preservation.json`).

Fresh foreground `make check-all PYTEST_WORKERS=2` passed: 14,457 backend tests
(97.41% coverage), 731 frontend tests (97.88% statement coverage), lint, formatting
and type checks (`/tmp/qf-w43-s26-check356.log`). No old test was edited or skipped,
and no generated record, frozen cohort or threshold changed.
