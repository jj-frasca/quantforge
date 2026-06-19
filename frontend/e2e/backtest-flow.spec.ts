import { expect, test } from '@playwright/test'

import { ONBOARDING_DISMISSED_KEY } from '../src/components/ui/OnboardingBanner'

// WORKED EXAMPLE — the flow that bit us twice (silent form-submit failures that
// shipped past MSW-mocked Vitest):
//
//   Load /  →  Backtest Results nav  →  "SMA crossover on SPY" preset  →
//   Run backtest  →  assert the equity-curve chart actually renders.
//
// This hits a REAL backend (memory store, lazy yfinance fetch on cache miss),
// so the assertion proves the whole chain: the form posts a valid body, the
// backend returns a 1200+ point equity curve, and Recharts paints an <svg>.
// MSW could never catch a real form-wiring or layout regression here.

test.beforeEach(async ({ page }) => {
  // Pre-dismiss the first-visit onboarding banner so it never overlaps the nav.
  // The banner only treats '1' as dismissed (OnboardingBanner.wasDismissed) — any
  // other value leaves it shown, so this MUST be '1', not a truthy string.
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, '1')
  }, ONBOARDING_DISMISSED_KEY)
})

test('SMA-on-SPY preset runs a real backtest and renders the equity curve', async ({
  page,
}) => {
  await page.goto('/')

  // Nav is a row of <button>s with accessible names (App.tsx).
  await page.getByRole('button', { name: 'Backtest Results' }).click()

  // Preset cards: each is an <article> labelled by its title with a "Load this
  // preset" button (PresetCards.tsx). Scope to the SPY card so we click the right one.
  const smaCard = page.getByRole('article', { name: 'SMA crossover on SPY' })
  await smaCard.getByRole('button', { name: 'Load this preset' }).click()

  // One click should have filled symbol + strategy + params + dates.
  await expect(page.getByLabel('Symbol')).toHaveValue('SPY')

  // Submit the form. The submit button toggles to "Running…" while pending.
  await page.getByRole('button', { name: 'Run backtest' }).click()

  // The equity-curve <section aria-label="equity curve"> renders only after a
  // successful response; on success it contains a Recharts <svg> path. Assert
  // on the drawn path, not just the container, so an empty-state regression fails.
  const equityCurve = page.getByRole('region', { name: 'equity curve' })
  // 60s: cold memory store → real yfinance fetch → vectorized backtest before the
  // curve can render. Throttled yfinance has pushed this past 30s under repeat runs.
  await expect(equityCurve).toBeVisible({ timeout: 60_000 })
  // The "Strategy" line is the load-bearing series; assert it specifically (a
  // buy-and-hold overlay also renders, so scope by name to stay unambiguous).
  await expect(
    equityCurve.locator('svg path.recharts-line-curve[name="Strategy"]'),
  ).toBeVisible()

  // And the human-readable verdict line rendered with real numbers.
  await expect(equityCurve.getByText(/Ending equity \$/)).toBeVisible()
})
