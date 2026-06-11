// groupByCategory: preserves canonical category order and per-category catalog order;
// omits empty categories; handles a single-category catalog.
import type { StrategyCatalog } from '../../types/strategies'
import { groupByCategory } from './groupByCategory'

const sample = (overrides: Partial<StrategyCatalog[number]>): StrategyCatalog[number] => ({
  name: 'x',
  label: 'X',
  category: 'Trend',
  description: '',
  citations: [],
  parameters: [],
  ...overrides,
})

test('groups entries by category and preserves canonical category ordering', () => {
  // Provide entries out of canonical order — Combination first, Trend last.
  const catalog: StrategyCatalog = [
    sample({ name: 'tfmr', category: 'Combination' }),
    sample({ name: 'don', category: 'Breakout' }),
    sample({ name: 'sma', category: 'Trend' }),
    sample({ name: 'momentum', category: 'Trend' }),
    sample({ name: 'mr', category: 'Mean Reversion' }),
  ]
  const groups = groupByCategory(catalog)
  expect(groups.map((g) => g.category)).toEqual([
    'Trend',
    'Mean Reversion',
    'Breakout',
    'Combination',
  ])
  // Within Trend, catalog order is preserved (sma then momentum, not alphabetical).
  expect(groups[0].entries.map((e) => e.name)).toEqual(['sma', 'momentum'])
})

test('omits categories with no entries (no empty headings rendered)', () => {
  const catalog: StrategyCatalog = [sample({ name: 'sma', category: 'Trend' })]
  const groups = groupByCategory(catalog)
  expect(groups.map((g) => g.category)).toEqual(['Trend'])
})

test('returns an empty array for an empty catalog', () => {
  expect(groupByCategory([])).toEqual([])
})
