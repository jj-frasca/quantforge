// defaultDateRange: returns YYYY-MM-DD strings anchored to `now`; trails `yearsBack`
// years for the start; rejects non-positive arguments. The `now` arg makes the
// behavior fully testable without mocking the system clock.
import { defaultDateRange } from './defaultDateRange'

// `process` isn't a typed global here (this tsconfig is browser-only, no @types/node) --
// it exists at runtime under Vitest's Node process, so read it through an explicit,
// narrowly-typed cast rather than pulling Node types into the whole app's typecheck.
const nodeProcess = (globalThis as unknown as { process: { env: Record<string, string | undefined> } })
  .process

// Built via the local-component constructor, not an ISO "Z" string: `defaultDateRange`
// deals in local calendar dates (see the timezone regression test below), so a fixture
// pinned to a UTC instant would assert against the wrong day depending on which
// timezone the suite happens to run in.
const NOON_JUNE_15 = new Date(2026, 5, 15, 12, 0, 0)

test('returns YYYY-MM-DD strings anchored to the supplied now', () => {
  const { startDate, endDate } = defaultDateRange(5, NOON_JUNE_15)
  expect(endDate).toBe('2026-06-15')
  expect(startDate).toBe('2021-06-15')
})

test('handles a 1-year window for short previews', () => {
  const { startDate, endDate } = defaultDateRange(1, NOON_JUNE_15)
  expect(startDate).toBe('2025-06-15')
  expect(endDate).toBe('2026-06-15')
})

test('rejects a non-positive yearsBack', () => {
  expect(() => defaultDateRange(0, NOON_JUNE_15)).toThrow(/positive/)
  expect(() => defaultDateRange(-1, NOON_JUNE_15)).toThrow(/positive/)
})

test('defaults `now` to the system clock when omitted', () => {
  // We don't pin the wall clock — just verify the shape is right.
  const { startDate, endDate } = defaultDateRange(5)
  expect(startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
  expect(endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/)
})

test('endDate matches the caller local calendar day, not the UTC day', () => {
  // Regression: toIsoDate used to format via toISOString().slice(0, 10), which reads
  // the UTC calendar date. For anyone west of UTC (most of the Americas), the local
  // evening is already tomorrow in UTC -- e.g. 11pm on June 15th in a UTC-7 zone is
  // 6am UTC on June 16th, so the form's "today" default silently became tomorrow.
  // Constructing `now` via the local-component Date constructor (not an ISO "Z"
  // string) plus pinning TZ here makes this deterministic regardless of the runner's
  // own default timezone: "11pm local on June 15" must read back as June 15,
  // wherever "local" is.
  const originalTz = nodeProcess.env.TZ
  nodeProcess.env.TZ = 'America/Los_Angeles' // UTC-7/UTC-8, west of UTC year-round
  try {
    const now = new Date(2026, 5, 15, 23, 0, 0) // June 15th, 11pm local
    const { endDate } = defaultDateRange(1, now)
    expect(endDate).toBe('2026-06-15')
  } finally {
    nodeProcess.env.TZ = originalTz
  }
})
