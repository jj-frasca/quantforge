// defaultDateRange: returns YYYY-MM-DD strings anchored to `now`; trails `yearsBack`
// years for the start; rejects non-positive arguments. The `now` arg makes the
// behavior fully testable without mocking the system clock.
import { defaultDateRange } from './defaultDateRange'

test('returns YYYY-MM-DD strings anchored to the supplied now', () => {
  const { startDate, endDate } = defaultDateRange(5, new Date('2026-06-15T12:00:00Z'))
  expect(endDate).toBe('2026-06-15')
  expect(startDate).toBe('2021-06-15')
})

test('handles a 1-year window for short previews', () => {
  const { startDate, endDate } = defaultDateRange(1, new Date('2026-06-15T00:00:00Z'))
  expect(startDate).toBe('2025-06-15')
  expect(endDate).toBe('2026-06-15')
})

test('rejects a non-positive yearsBack', () => {
  expect(() => defaultDateRange(0, new Date('2026-06-15T00:00:00Z'))).toThrow(/positive/)
  expect(() => defaultDateRange(-1, new Date('2026-06-15T00:00:00Z'))).toThrow(/positive/)
})

test('defaults `now` to the system clock when omitted', () => {
  // We don't pin the wall clock — just verify the shape is right.
  const { startDate, endDate } = defaultDateRange(5)
  expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
})
