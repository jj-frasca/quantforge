# ADR-116: Verify fiscal-year adjacency before computing revenue_growth_yoy

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session #102 (delegated authority, AUTONOMY_CHARTER.md §1)
- **Resolves**: FINDING-044

## Context

`parse_company_facts` (`app/data/fundamentals.py`) derives `revenue_growth_yoy` from the last two
rows of `_annual_facts`'s fiscal-year-sorted output, indexing `revenue_rows[-2]` as "the prior
year" without checking its fiscal year. `_annual_facts` only returns fiscal years actually present
in the filer's `us-gaap` XBRL facts, so a gap (fiscal-year-end change, a restated filing that
supersedes rather than adds a row, an unusual filer history) means `revenue_rows[-2]` can be two or
more fiscal years before `fiscal_year`. The field is still named and consumed as a year-over-year
rate downstream (`screen_fundamentals`, valuation scoring), so a silent multi-year figure there is
a mislabeled claim, not just an edge case.

## Options Considered
1. **Require exact adjacency (`fy == fiscal_year - 1`); otherwise `None`.**
   - Pro: matches the existing "cannot verify" convention `screen_fundamentals` already applies
     when the prior year is missing outright — a gap of 2+ years is the same kind of unverifiable
     as a gap of "no prior year at all," just less extreme.
   - Pro: zero new fields, zero new config; a one-line guard at the existing call site.
   - Con: a name with a genuine one-off filing gap (e.g., a fiscal-year-end change) loses a growth
     figure for that snapshot rather than reporting an approximate one.
2. **Compute a CAGR-style annualized rate over however many years actually separate the two rows.**
   - Pro: still produces a number instead of `None`.
   - Con: changes the field's meaning (annualized multi-year vs. single-year) silently; a consumer
     comparing `revenue_growth_yoy` across symbols would be comparing different statistics without
     knowing it. Would need a new field name and schema change to be honest about it — out of
     scope for a data-honesty bug fix.
3. **Leave as-is; document the limitation in a docstring.**
   - Con: a docstring does not stop `screen_fundamentals` or valuation scoring from silently
     consuming a mislabeled number today. CLAUDE.md rule 6 requires the code, not just the prose,
     to be honest about what it can verify.

## Decision

Guard the existing computation: `revenue_growth_yoy` is populated only when
`int(revenue_rows[-2]["fy"]) == fiscal_year - 1`. Otherwise it stays `None`, identical to the
already-tested "no prior year at all" path. No new field, no new config, no change to
`parse_company_facts_history` (which reports raw per-fiscal-year figures and makes no YoY claim).

## Consequences

- A fiscal-year gap now yields `revenue_growth_yoy = None` instead of a silently mislabeled
  multi-year rate. `screen_fundamentals`'s "unavailable (cannot verify)" branch already handles
  `None` correctly, so no downstream change is needed.
- A name with a genuine filing gap reports fewer growth figures across its history. This is the
  conservative, honest direction (CLAUDE.md rule 6) and matches the project's existing bias:
  `screen_fundamentals`'s docstring already states a metric it cannot verify fails its check.
- Reversible: remove the fiscal-year equality guard, reverting to the unconditional
  `revenue_rows[-2]` read. Not recommended — that restores the mislabeling this ADR fixes.
