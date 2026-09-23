# FINDING-040: Sharpe interval hides its iid-normal assumption

- **Severity:** Medium
- **Status:** Resolved by ADR-111
- **Found:** 2026-09-23, Codex autonomous session 8
- **Affects:** Backtest Sharpe confidence interval, API, and dashboard

## Finding

ADR-109 implements the iid-normal asymptotic Sharpe interval
`sqrt((1 + SR^2 / 504) / years)` but the API calls it only `sharpe_ci` and the dashboard renders
“95% CI” plus an unqualified sampling-noise explanation. Nothing in the durable response or visible
label states the independence/normality assumption.

That omission is material for strategy returns. Position persistence, overlapping lookbacks, and
time-varying volatility can create serial dependence and non-normal moments. Lo (2002), the paper
ADR-109 cites, derives separate results for iid and stationary returns and documents that serial
correlation can substantially change annualized Sharpe inference. The implemented interval depends
only on sample mean, standard deviation, and length: permuting the same returns leaves it identical,
so it cannot account for temporal dependence.

The helper also accepts any `confidence` float. Values at or above one produce infinite or `NaN`
bounds; zero collapses the range to the point estimate; negative values reverse the quantiles. The
default API path always passes 0.95, but a public statistical boundary must reject invalid domains
rather than return malformed evidence.

## Required correction

Preserve the existing estimator as an explicitly labelled iid-normal descriptive interval rather
than silently replacing it with an unreviewed HAC/bootstrap method. Carry the assumption in the
backend record, API schema, frontend parser, and rendered label/explanation. Require finite
`0 < confidence < 1` before calculation. Add regressions for the durable assumption field, visible
qualified label, and invalid confidence values. Do not change the Sharpe point estimate, gate,
validation threshold, calibration identity, workflow, or generated data.
