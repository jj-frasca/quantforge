/**
 * Whether a `[startDate, endDate]` pair (both YYYY-MM-DD) would pass the backend's own
 * range contract (ADR-133 `validate_request_range`): strictly ordered, start before end.
 * Lexicographic comparison on YYYY-MM-DD strings is chronological order — no Date parsing
 * needed. Every date-range form should check this before submit so a user sees an inline
 * message instead of a 422 (FINDING-064): the backend now rejects equal/reversed bounds
 * that used to reach it silently.
 */
export function isValidDateRange(startDate: string, endDate: string): boolean {
  return startDate < endDate
}
