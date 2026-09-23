# FINDING-045: Piotroski F-Score trend signals assume the prior row is the adjacent fiscal year

- **Severity:** Medium
- **Status:** Resolved by ADR-117
- **Found:** 2026-09-23, Autonomous session #102
- **Affects:** `piotroski_f_score` (`app/research/fundamentals/quality.py`, ADR-029 Layer 2)

## Finding

`piotroski_f_score` takes `t, p = years[-1], years[-2]` from a `FundamentalsHistory` and treats
`p` as the fiscal year immediately preceding `t` for all six trend (`delta_*`/`no_dilution`)
signals, with no check that `p.fiscal_year == t.fiscal_year - 1`. `FundamentalsHistory.years`
comes from `parse_company_facts_history`, which only includes fiscal years actually present in the
filer's XBRL facts (see FINDING-044, the same root cause in the sibling snapshot parser) — a gap
is possible from a fiscal-year-end change or a restated filing that drops a year. When a gap
exists, `years[-2]` is two or more years before `t`, and every trend signal
(`delta_roa_positive`, `delta_leverage_negative`, `delta_current_ratio_positive`, `no_dilution`,
`delta_gross_margin_positive`, `delta_asset_turnover_positive`) silently compares across a
multi-year span instead of one year, inflating or deflating the F-Score (0-9) without any
indication in the result that the comparison window was wider than the score's definition
requires.

This module's own docstring states the conservative principle this violates: "a signal is False
when its inputs are missing (never award a point on absent data)." A non-adjacent prior year is
exactly as unverifiable, for a *year-over-year* score, as a missing prior year — the code just
didn't check for it.

## Required correction

Gate the six trend signals on `p.fiscal_year == t.fiscal_year - 1`; when false, treat `p` as
unavailable for every trend computation (same "None -> no point" convention already used for
missing individual fields). The three level-only signals (`roa_positive`, `cfo_positive`,
`accruals_quality`) are unaffected since they only read `t`. `financial_safety` and
`gross_profitability` (the module's other two scorers) read only `years[-1]` and make no
year-over-year claim, so neither needs this guard.
