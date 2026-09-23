// Compact currency for chart axis labels ($1.2M, $92.5K, ...). Split out of
// EquityCurvePanel.tsx so it can be unit-tested directly — it's only ever invoked through
// recharts' tickFormatter prop, which jsdom doesn't exercise without real chart layout — and
// so a component file doesn't export a non-component (react-refresh/only-export-components).
export const fmtCompact = (value: number): string =>
  `$${value.toLocaleString('en-US', { notation: 'compact', maximumFractionDigits: 1 })}`
