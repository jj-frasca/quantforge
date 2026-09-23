# FINDING-044: revenue_growth_yoy assumes the prior row is the adjacent fiscal year

- **Severity:** Medium
- **Status:** Resolved by ADR-116
- **Found:** 2026-09-23, Autonomous session #102
- **Affects:** `parse_company_facts` (SEC EDGAR fundamentals parsing, ADR-017)

## Finding

`parse_company_facts` computes `revenue_growth_yoy` from `revenue_rows[-2]`, the second-to-last
annual revenue row, without checking that its fiscal year is `fiscal_year - 1`. `_annual_facts`
returns one row per fiscal year present in the filer's XBRL data, sorted ascending, but a fiscal
year can be absent — a fiscal-year-end change, a gap in filed 10-Ks, or a restatement that drops a
year. When that happens, `revenue_rows[-2]` is two or more years back, and the resulting figure is
silently labeled `revenue_growth_yoy` even though it is a multi-year compound change, not a
year-over-year one. `FundamentalScreen` and any downstream consumer (valuation scoring, the
fundamentals sweep) would then screen or rank a name on a mislabeled growth rate.

This is a data-honesty violation of the same kind CLAUDE.md rule 6 states for quality checks: the
field name is a specific claim ("year over year") that the code does not verify before making it.

## Required correction

Only populate `revenue_growth_yoy` when `revenue_rows[-2]`'s fiscal year is exactly
`fiscal_year - 1`. Otherwise leave it `None`, the same "cannot verify" convention
`screen_fundamentals` already applies to a missing prior year entirely. No change to
`parse_company_facts_history`, which reports each year's raw figures per fiscal year and makes no
YoY claim.
