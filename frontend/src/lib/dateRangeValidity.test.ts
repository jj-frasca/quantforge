// isValidDateRange: mirrors the backend's own strictly-ordered range contract
// (ADR-133's validate_request_range — naive/equal/reversed all rejected) so a user gets
// an inline message before submitting, not just a 422 after.
import { isValidDateRange } from './dateRangeValidity'

test('accepts a start strictly before end', () => {
  expect(isValidDateRange('2020-01-01', '2020-01-02')).toBe(true)
})

test('rejects equal start and end (backend requires strictly ordered bounds)', () => {
  expect(isValidDateRange('2020-01-01', '2020-01-01')).toBe(false)
})

test('rejects a reversed range', () => {
  expect(isValidDateRange('2020-06-01', '2020-01-01')).toBe(false)
})
