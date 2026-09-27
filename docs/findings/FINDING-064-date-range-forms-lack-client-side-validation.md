# FINDING-064: Date-range forms lack client-side validation for equal/reversed ranges

- **Severity:** Low
- **Status:** Resolved (this commit)
- **Found:** 2026-09-27
- **Area:** Frontend forms (Backtest Results, Validation Report, Compare Configs, Data Explorer)

## Finding

ADR-132/ADR-133 made the backend strictly reject naive, equal, or reversed `[start_date, end_date)`
request ranges with a 422 across `/backtest`, `/validate`, `/monte-carlo`, `/bars`, and `/ingest`.
Every frontend form that submits a date range (`BacktestResultsPage.tsx`, `ValidationReportPage.tsx`,
`CompareConfigsPage.tsx`, `DataExplorerPage.tsx`) already sends timezone-aware payloads via a shared
`toIsoStartOfDay` convention, so the naive-datetime shape of the 422 is unreachable through the UI.
But none of the four `<input type="date">` pairs constrain start relative to end, so a user can pick
`start == end` or `start > end` and submit.

Verified this does not crash anything: the shared API-client error path
(`services/backtest.ts`/`services/api.ts`/`services/bars.ts`) reads `body.detail` on any non-2xx
response and every consuming page renders an explicit `role="alert"` error state. The gap is
strictly a missing pre-submit guard, not a crash or a silent failure — a user would see a rendered,
if slightly technical, 422 message rather than nothing.

## Impact

- A user who picks an equal or reversed date range gets a round trip to the backend to learn what a
  client-side check could have told them immediately.
- No Monte Carlo form exists in the frontend today, so that endpoint's own validation is not
  reachable through the UI (moot, not part of this fix).

## Resolution

Added `frontend/src/lib/dateRangeValidity.ts` (`isValidDateRange`, lexicographic comparison on
`YYYY-MM-DD` strings — chronological order, matching the backend's strictly-ordered contract) and
wired it into all four forms: submit is disabled and an inline `role="alert"` message
("Start date must be before end date.") renders whenever the current start/end selection would be
rejected. TDD: one new test per page reproduces the exact reachable shape (equal, then reversed,
then a valid range clearing the message) — RED before the guard existed, GREEN after.
