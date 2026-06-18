// PresetCards: 4 "Try these first" cards above the Backtest Results form. Each card is
// a one-click load of a canonical (symbol, strategy, params, window) setup. Clicking a
// card invokes onLoad with the preset payload.
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, test, vi } from 'vitest'

import { PresetCards } from './PresetCards'
import { PRESETS } from './presets'

test('renders one card per preset', () => {
  render(<PresetCards onLoad={() => {}} />)
  const cards = screen.getAllByRole('article')
  expect(cards).toHaveLength(PRESETS.length)
  // The four presets — three pass-cleanly contrasting methodologies + one "honest
  // loser" (Triple MA) to demonstrate the validation engine. Card titles include the
  // canonical method name so the user maps each preset back to the catalog dropdown.
  expect(screen.getByText(/sma crossover/i)).toBeInTheDocument()
  expect(screen.getByText(/rsi mean reversion/i)).toBeInTheDocument()
  expect(screen.getByText(/donchian breakout/i)).toBeInTheDocument()
  expect(screen.getByText(/triple ma alignment/i)).toBeInTheDocument()
})

test('clicking a preset card calls onLoad with that preset', async () => {
  const onLoad = vi.fn()
  render(<PresetCards onLoad={onLoad} />)
  // Pick the first preset and click its load button.
  const goldenCross = PRESETS[0]
  const buttons = screen.getAllByRole('button', { name: /load this preset/i })
  await userEvent.click(buttons[0])
  expect(onLoad).toHaveBeenCalledTimes(1)
  expect(onLoad).toHaveBeenCalledWith(goldenCross)
})

test('each preset carries a symbol + strategy.name that the catalog can render', () => {
  // Guard rail: a preset whose strategy.name doesn't exist in the backend catalog
  // would silently no-op on load. Asserting the union here means a typo in
  // presets.ts fails CI instead of failing silently in the browser.
  const catalogNames = new Set([
    'sma',
    'momentum',
    'mean_reversion',
    'rsi_mean_reversion',
    'donchian_breakout',
    'bollinger_bands',
    'macd',
    'vol_targeted_sma',
    'keltner_channel',
    'trend_filtered_mean_reversion',
    'triple_ma_alignment',
  ])
  for (const preset of PRESETS) {
    expect(preset.symbol).toMatch(/^[A-Z]{1,5}$/)
    expect(catalogNames.has(preset.strategy.name)).toBe(true)
    expect(preset.yearsBack).toBeGreaterThan(0)
  }
})
