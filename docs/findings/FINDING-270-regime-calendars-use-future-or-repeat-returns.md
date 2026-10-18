# FINDING-270: Regime calendars can use future or repeated observations

- **Status:** Resolved — ADR-319 original-calendar guards
- **Date:** 2026-10-18
- **Scope:** Original source indexes at public analyze_regimes

## Reproduction

With identical unique indexes ordered January1, January3, January2, January4
and positive window1, alignment retains the supplied nonmonotonic order. Hold
strategy returns fixed and market prices initially100. Changing only January3's
price to200 moves January2's unchanged return from bull to bear. A wrapper
records the actual timestamps passed to each regime's Sharpe calculation,
then delegates to the original metric. The later calendar price therefore
changes an earlier return's group even after ADR-318 refuses negative horizons.
Parent and independent witnesses reproduce this directly.

Duplicate originals create a distinct identity failure at the same boundary.
A three-row strategy series indexed January1 twice and January2 once, aligned
against market prices indexed January1 three times and January2 once, becomes
seven rows. Regime counts sum to7 and strategy returns are repeatedly
compounded/scored. Identical duplicate indexes can also place observations
at one timestamp into different regimes. Counts of aligned rows do not establish
unique original observations.

Written independent review: `/tmp/qf-w42-s33-regime-calendar-review.md`.
Parent receipt: `/tmp/qf-w42-s33-regime-calendar-parent-probe.json`.
These are direct malformed-source diagnostic witnesses, not production search,
calibration, strategy or false-graduation observations.

## Correction and limits

Normal ValidationEngine uses the backtest engine's unique ascending calendar
check and constructs returns and market prices from the same frame. That
mitigates its current route; no affected production result is established.
ADR-319 requires both complete original indexes to be unique and ascending
after the existing window guard and before alignment, without sorting or
choosing among duplicates. Even invalid rows outside the intersection refuse.

Default20, zero horizons, ordered generic/naive/aware sources, empty/singleton
inputs and the existing partial-intersection policy retain their behavior.
All alignment, trailing-label, grouping, product and Sharpe statements stay.
No schema, gate, threshold, search identity, v14, generated record or cohort
changes. Index order does not establish actual daily cadence, source provenance,
price validity or an executable switching account. Native timezone/alignment
limitations and finite arithmetic remain separate.

## Verification

Twenty-four valid pre-edit payloads are frozen in
`/tmp/qf-w42-s33-regime-calendar-baseline.json`, SHA256
`1ba109355bc4929d3fdd3feb94454270a27018d6147318841a56e36f810eaa25`.
They cover generic, naive, UTC, zero/positive horizons, partial/disjoint
intersections, empty and singleton sources. Original source SHA256:
`66921e3071107c8ef6706fadb7dbcf1ccf57bc63c9eb972a7d2ceff6ec78adb1`.
Independent precode scope review approved. The final actual preimplementation
run observed17 failures and15 preserved controls in9.07s, with production diff
empty (`/tmp/qf-w42-s33-regime-calendar-red-final.log`). An earlier17/15 run
in8.86s is retained; only regex raw-literal spelling changed before final RED.
After implementation all32 new tests plus33 existing regime/horizon tests
passed (parent3.71s, independent3.79s). Tests cover both original calendars,
refusal before alignment, invalid rows outside the intersection, actual future
and duplicate-expansion witnesses, count-check precedence, index compatibility
and Hypothesis rotated-order/unique-intersection/nonmutation properties.
Ruff, formatting and mypy186 passed.

Separate parent and independent audits preserve all24 valid complete payloads
exactly. The entire prior module AST remains identical after removing only
the calendar loop and restoring the original docstring: ADR-318's window guard
and every alignment/label/group/product/Sharpe statement remain intact.
Parent receipt `/tmp/qf-w42-s33-calendar-parent-audit.json`, SHA256
`3db654cafe65c9f662568419f3670eaa4e0cd0245333512b6bfc604cd0ac6eca`.
Independent receipt `/tmp/qf-w42-s33-regime-calendar-final-audit.json`, SHA256
`32c7a75e1b67daa4b954cc0147709b018a9401cd615c52ea790aab2af9ef62fd`.
Final source SHA256:
`3ead68e99542d824045790a4edc9012f6499faa8383a346d04bd449c61371a87`.
Prior tests, helper, frontend and generated data retain their bytes.
Independent final five-path research review approved. Fresh foreground
`make check-all PYTEST_WORKERS=4` passed12989 backend tests (97.39% coverage)
and438 frontend tests (97.69% statement coverage), with lint, formatting and
strict typing green. Log `/tmp/qf-w42-s33-check319.log`. All verification closed;
production source stayed frozen after focused GREEN.
