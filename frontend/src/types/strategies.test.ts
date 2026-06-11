// Zod boundary: parse a valid catalog; reject unknown param `type`; reject a missing
// required field.
import { strategyCatalogSchema } from './strategies'

const valid = [
  {
    name: 'sma',
    label: 'SMA Crossover',
    category: 'Trend' as const,
    description: 'Trend-following baseline.',
    citations: ['textbook'],
    parameters: [
      {
        name: 'fast',
        type: 'int' as const,
        default: 20,
        minimum: 1,
        maximum: 200,
        label: 'Fast window',
        description: null,
      },
    ],
  },
]

test('strategyCatalogSchema parses a valid catalog', () => {
  expect(strategyCatalogSchema.parse(valid)).toEqual(valid)
})

test('strategyCatalogSchema rejects an unknown param type', () => {
  const bad = [
    {
      ...valid[0],
      parameters: [{ ...valid[0].parameters[0], type: 'string' }],
    },
  ]
  expect(() => strategyCatalogSchema.parse(bad)).toThrow()
})

test('strategyCatalogSchema rejects an unknown category', () => {
  // If the backend adds a new StrategyCategory variant, the frontend Zod enum has to
  // be extended in the SAME commit; otherwise every entry with the new category will
  // fail the boundary parse. This test makes that contract enforceable.
  const bad = [{ ...valid[0], category: 'Carry' }]
  expect(() => strategyCatalogSchema.parse(bad)).toThrow()
})

test('strategyCatalogSchema rejects a missing description on the entry', () => {
  const incomplete: Record<string, unknown> = { ...valid[0] }
  delete incomplete.description
  expect(() => strategyCatalogSchema.parse([incomplete])).toThrow()
})
