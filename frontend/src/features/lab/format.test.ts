import { fmtCompact } from './format'

// fmtCompact backs the equity-curve chart's Y-axis labels ($1.2M, $92.5K, ...) — it's only
// ever invoked through recharts' tickFormatter prop, which jsdom doesn't exercise without
// real chart layout, so a direct call here is the only real check on its output.
test('fmtCompact formats values as compact currency', () => {
  expect(fmtCompact(1_234_567)).toBe('$1.2M')
  expect(fmtCompact(1_500)).toBe('$1.5K')
  expect(fmtCompact(999)).toBe('$999')
  expect(fmtCompact(0)).toBe('$0')
  // Equity is always >= 0 in practice, but the sign lands after the '$' rather than before
  // it (the template is `$${...}`, and toLocaleString puts the minus on the number) — an
  // easy-to-miss quirk if this function is ever reused somewhere negative values are real.
  expect(fmtCompact(-92_488.99)).toBe('$-92.5K')
})
