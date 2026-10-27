# FINDING-322: FY/form filtering does not verify annual fact periods

- **Status:** Open — reporting clarified; production period policy unmeasured
- **Date:** 2026-10-26, Codex autonomous session 3 (ISO2026-W44)
- **Severity:** Potential methodology risk; production incidence unestablished
- **Affected:** _annual_facts, parse_company_facts and parse_company_facts_history
- **Related:** ADR-017/022/029; distinct from ADR-116/117's year-adjacency guards

## Confirmed code behavior

The shared selector filters fp == FY and form starting with 10-K, sorts by filed,
and keeps the last row per reported fy. It does not examine start/end duration,
frame, observation-period identity or same-filing ambiguity. Equal filed values
retain input order, making the last input row win a collision. The former
full-year docstring therefore described a guarantee the code does not implement.

At producing revision 0b759d02, a synthetic prior annual revenue is 100. The next
reported fy has annual revenue 120 and a short-period revenue 40, sharing the same
filed date, accession, form, fy and fp. Annual net income is 12. Ordering the short
row last selects revenue 40, growth -60%, margin 30% and a failed default screen.
Reversing those two rows selects 120, growth 20%, margin 10% and a passing screen.
Neither path refuses the mixed periods. A third accepted-shape case lets a
comparative-period row produce reported fy 2024 with period_end 2023-12-31.
Parent and independent data-engineering probes confirm these synthetic behaviors.
No source acquisition or search is needed for the witnesses.

These inputs demonstrate accepted-shape behavior, not that SEC CompanyFacts emits
the exact constructed rows. No actual affected vendor row, production experiment,
false graduate or trading effect is established.

## Primary-source context and limits

The [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
says CompanyFacts aggregates company concepts across submissions and describes
annual, quarterly and instantaneous frame periods separately. The
[SEC Financial Statement Data Sets documentation](https://www.sec.gov/dera/data/fsds.pdf)
§3 describes filings containing multiple reporting periods; its submission fields
and numeric fact period-end/duration fields are separate. The
[EDGAR XBRL Guide, June 2026](https://www.sec.gov/files/edgar/filer-information/specifications/xbrl-guide-2026-06-29.pdf)
§3.1.8, printed page 32, defines fiscal period focus for the report.

Those sources support the distinction between reporting focus and fact periods.
They do not, in this review, establish the exact CompanyFacts JSON fy/fp mapping
or identify a real affected CompanyFacts row. Transferring the FSDS field meanings
to that JSON without further evidence would be an inference, not verified schema
identity. The risk to real production remains unmeasured.

## Disposition

Correct only the three parser docstrings and cold-memory claims. Preserve all
filtering, ordering, tie handling, fiscal labels, arithmetic, source calls and
screening behavior. This reporting correction does not close period selection.

A runtime correction requires an attributable frozen CompanyFacts fixture, a
separate ADR and TDD for duration concepts versus instantaneous balances,
non-December fiscal calendars, comparative periods, restatements and ambiguous
ties. Assigning fiscal years from end.year or applying one duration filter to
all concepts would introduce unsupported assumptions. Existing adjacency checks
operate after year assignment and do not establish observation-period identity.
No threshold, search, v14, generated record or frozen cohort changes.

## Verification

Final independent data-engineering and research reviews approved this reporting-only
correction in Codex session 5. Both separately checked the module against HEAD:
only the three intended docstrings differ. The data review independently rebuilt
all three synthetic witnesses. Foreground make check-all passed: 15,253 backend
tests (97.43% coverage), 746 frontend tests (97.88% statement coverage), lint,
formatting and types. No new behavior or TDD implementation claim is made.

Three complete synthetic claims and a prepatch module AST/docstring receipt are
preserved at /tmp/qf-w44-s3-period-probe.{py,json}; --compare checks unchanged
claims and the whole module AST except the three permitted docstrings without
writing receipts. Run from backend with PYTHONPATH=. and the offline UV cache.
The parent replay passed in session 5.
Official source text was verified through the web reader. Direct PDF download
returned HTTP 403; no rendered-table verification or CompanyFacts acquisition is
claimed.
