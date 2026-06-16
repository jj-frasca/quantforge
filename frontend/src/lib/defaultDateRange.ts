/**
 * Compute a sensible default `[startDate, endDate]` for a form, anchored to TODAY.
 *
 * Returns YYYY-MM-DD strings — that's what `<input type="date">` expects, and what the
 * form's `toIsoStartOfDay(...)` already converts to the backend's ISO format.
 *
 * Why a helper: the form defaults used to be hardcoded ("2020-01-01" / "2024-01-01"),
 * which turned into "the dates are years in the past" once the project sat on master
 * for a while. Anchoring to `Date.now()` keeps every form's defaults trailing the
 * current day, so a new visitor never has to first realise the date picker is stale.
 *
 * yfinance handles `end >= today` by returning up through the last available bar — no
 * special handling needed on our side. Trading-day vs calendar-day math is also a
 * non-issue: a 5-year trailing window is ~1260 trading bars (≈ 252 × 5), comfortably
 * past the longest catalog warmup (trend_window=100, slow=100). 1 year is ~252 bars,
 * still fine for short-window strategies the Data Explorer is used to preview.
 */
export interface DateRange {
  startDate: string
  endDate: string
}

export function defaultDateRange(yearsBack: number, now: Date = new Date()): DateRange {
  if (!Number.isFinite(yearsBack) || yearsBack <= 0) {
    throw new Error(`yearsBack must be a positive number; got ${yearsBack}`)
  }
  const start = new Date(now)
  start.setFullYear(start.getFullYear() - yearsBack)
  return {
    startDate: toIsoDate(start),
    endDate: toIsoDate(now),
  }
}

function toIsoDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}
