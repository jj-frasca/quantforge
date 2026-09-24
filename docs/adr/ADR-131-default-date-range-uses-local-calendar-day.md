# ADR-131: Form date defaults use the local calendar day, not UTC

- **Status:** Accepted
- **Date:** 2026-09-24
- **Deciders:** Claude autonomous session 106
- **Resolves:** FINDING-059

## Context

`defaultDateRange` formats its `startDate`/`endDate` via `toIsoDate`, which used
`date.toISOString().slice(0, 10)` — the UTC calendar date. The function's own stated purpose is to
anchor every form's date defaults to "today" from the visitor's perspective. For anyone west of UTC
(most of the Americas) during local evening hours, the UTC calendar date is already tomorrow, so the
form silently defaulted to tomorrow's date instead of today's — see FINDING-059.

## Options Considered

1. **Format via local `Date` getters (`getFullYear`/`getMonth`/`getDate`) instead of
   `toISOString()`.**
   - Pro: matches the function's stated intent exactly — a plain `<input type="date">` has no
     timezone semantics of its own; "today" on a date picker means the visitor's local calendar
     day. Minimal diff, no API change.
   - Con: none identified for this function's actual use (a UI default, not a value stored/compared
     server-side in UTC).
2. **Keep UTC, document the caveat.**
   - Con: doesn't fix the actual defect — every consuming form still shows tomorrow's date for a
     large fraction of the day for users west of UTC, which is precisely the bug this function was
     written to prevent (the file's own docstring history: it replaced hardcoded stale dates for
     exactly this "don't confuse a new visitor" reason).
3. **Use `Intl.DateTimeFormat` with an explicit `timeZone` option instead of raw getters.**
   - Con: more machinery for the same result; raw local getters are simpler and already
     unambiguous for a plain calendar-date (no time-of-day) use case.

Chose option 1.

## Decision

`toIsoDate` now builds the `YYYY-MM-DD` string from `date.getFullYear()`, `date.getMonth() + 1`, and
`date.getDate()` (local components), instead of `date.toISOString().slice(0, 10)`.

## Consequences

- Every form using `defaultDateRange` (Backtest Results, Compare Configs, Validation Report, Data
  Explorer) now defaults to the visitor's actual local "today," matching the function's documented
  intent, at all times of day.
- The existing unit tests' fixtures (previously UTC-ISO timestamps that happened to line up with
  local dates only by coincidence of running in UTC CI) were rewritten to construct `now` via the
  local-component `Date` constructor, which is unambiguous regardless of the runner's timezone.
- Added a regression test that pins `TZ` to a negative-UTC-offset zone for one assertion (restored
  after) so the fix is verified deterministically in CI, not just on a developer's own machine.

## Reversal

Revert `toIsoDate` to `date.toISOString().slice(0, 10)`. Not recommended — reintroduces
FINDING-059's silent tomorrow-instead-of-today default for users west of UTC.
