# ADR-117: Gate Piotroski F-Score trend signals on fiscal-year adjacency

- **Status**: Accepted
- **Date**: 2026-09-23
- **Deciders**: Autonomous session #102 (delegated authority, AUTONOMY_CHARTER.md §1)
- **Resolves**: FINDING-045
- **Same root cause as**: ADR-116 (`revenue_growth_yoy`, `app/data/fundamentals.py`)

## Context

`piotroski_f_score` (`app/research/fundamentals/quality.py`) reads `t, p = years[-1], years[-2]`
and uses `p` as "the prior fiscal year" for six of the F-Score's nine components without verifying
`p.fiscal_year == t.fiscal_year - 1`. `FundamentalsHistory.years` only contains fiscal years the
filer actually reported (built by `parse_company_facts_history` from `_annual_facts`'s
fiscal-year-sorted output), so a gap is possible for the same reasons ADR-116 already documented
for `revenue_growth_yoy`: a fiscal-year-end change, or a restated filing that supersedes rather
than adds a row. When a gap exists, the F-Score's trend components silently become multi-year
comparisons while still being reported as single-year (0-9, Piotroski 2000) signals.

## Options Considered
1. **Gate all six trend signals on exact adjacency; non-adjacent `p` scores those signals `False`
   (same as a missing field).**
   - Pro: matches the module's own stated conservative principle exactly — "never award a point
     on absent data" already applies to missing *fields*; a non-adjacent year is unverifiable for
     the same reason.
   - Pro: the three level-only signals (`roa_positive`, `cfo_positive`, `accruals_quality`) are
     untouched — they only need `t`, so a gap in `p` shouldn't zero those out too.
   - Con: a filer with any historical gap scores lower on the trend components even where the
     underlying trend might still be knowable some other way (e.g. interpolation) — not attempted
     here; the ADR-116 precedent already chose "report nothing" over "report an approximation."
2. **Search `years` for the true `t.fiscal_year - 1` row instead of assuming `years[-2]`.**
   - Pro: would recover a valid comparison if the immediately-prior year exists somewhere earlier
     in the tuple but isn't at index -2 (e.g., duplicate/out-of-order entries).
   - Con: `parse_company_facts_history` already de-duplicates and sorts ascending by construction
     (confirmed by reading `_year_value_map`/the `years` build loop), so `years[-2]` is already
     the second-most-recent *available* year; the only failure mode is a genuine gap, which this
     option cannot fix (there is no row to find). Added complexity with no behavior difference.
3. **Leave as-is; document the limitation in the docstring only.**
   - Con: same objection as ADR-116 option 3 — a docstring doesn't stop the score from being
     computed and consumed as an accurate signal today.

## Decision

Compute `p_adjacent = p.fiscal_year == t.fiscal_year - 1` once, immediately after
`t, p = years[-1], years[-2]`. Use it to gate `roa_p`, `lev_p`, `cr_p`, `gm_p`, `at_p` (set `None`
when not adjacent, flowing through the existing None-safe comparisons unchanged) and `no_dilution`
(added directly to its boolean expression, since it reads `p.shares_diluted` without going through
`_ratio`). No change to `financial_safety` or `gross_profitability`, which read only `years[-1]`.

## Consequences

- A fiscal-year gap now scores the six trend components `False` instead of comparing across a
  multi-year span silently. The three level-only components are unaffected.
- Consistent with ADR-116: both fixes convert an unverified "adjacent year" assumption into an
  explicit check, using the same "unverifiable -> no point / no value" convention already
  established elsewhere in the fundamentals code (`screen_fundamentals`, this module's own
  docstring).
- Reversible: remove the `p_adjacent` guard and inline it back to unconditional `p` reads. Not
  recommended — that restores the mislabeled multi-year comparison this ADR fixes.
