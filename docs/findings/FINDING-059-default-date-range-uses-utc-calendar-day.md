# FINDING-059: Form date defaults can silently show tomorrow's date

- **Severity:** Medium
- **Status:** Resolved by ADR-131
- **Found:** 2026-09-24, autonomous session 106 (cold-directory audit of `frontend/src/lib/`,
  cold since 2026-06-15)
- **Affects:** `defaultDateRange` (`frontend/src/lib/defaultDateRange.ts`), consumed by
  `BacktestResultsPage`, `CompareConfigsPage`, `ValidationReportPage`, `DataExplorerPage`

## Finding

`defaultDateRange`'s own docstring states its purpose plainly: "Anchoring to `Date.now()` keeps
every form's defaults trailing the current day, so a new visitor never has to first realise the
date picker is stale." Its `toIsoDate` helper formatted dates via
`date.toISOString().slice(0, 10)` — which reads the **UTC** calendar date, not the caller's local
calendar date.

`Date.prototype.toISOString()` always converts to UTC before formatting. For anyone in a timezone
west of UTC (most of the Americas, roughly UTC-4 to UTC-10), the local evening is already the next
UTC calendar day. Concretely, in `America/Los_Angeles` (UTC-7 during PDT): 11pm on June 15th local
is 6am UTC on June 16th. Every form using `defaultDateRange` — the Backtest Results form, the
Compare Configs form, the Validation Report form, the Data Explorer's default range — would silently
default `endDate` (and, shifted by the same amount, `startDate`) to tomorrow's date for a large
fraction of the day, for a large fraction of the userbase, defeating the exact "trailing the current
day" guarantee this helper exists to provide.

This was invisible to the existing test suite because every fixture pinned `now` to a UTC-anchored
ISO timestamp (`new Date('2026-06-15T00:00:00Z')` / `...T12:00:00Z`), and CI runs on a UTC-default
GitHub Actions runner — so `toISOString()`'s UTC read matched the fixture's own UTC-anchored
"local" expectation by construction, in every environment the suite actually ran in. It reproduces
immediately on a real developer machine set to a non-UTC timezone (confirmed live on this session's
own `America/Los_Angeles` machine).

## Reproduction

```js
// TZ=America/Los_Angeles
const now = new Date(2026, 8, 24, 20, 0, 0) // Sep 24, 8pm local
now.toISOString().slice(0, 10) // "2026-09-25" -- tomorrow, not today
```

## Test-suite note

The regression test (`defaultDateRange.test.ts`) pins `process.env.TZ` to a specific negative-UTC-
offset zone for the duration of one test (restored in a `finally`), and constructs `now` via the
local-component `Date` constructor rather than a UTC ISO string, so the assertion is deterministic
regardless of the runner's own default timezone — it would have failed identically in CI (UTC) had
it been written before the fix, unlike a naive reproduction that only manifests outside UTC.
