import { expect, test } from '@playwright/test'

import { ONBOARDING_DISMISSED_KEY } from '../src/components/ui/OnboardingBanner'

// Browser-driven verification of ADR-011 / Compare Configs page. The Vitest tests
// exercise rendering and per-row error handling against MSW; this spec proves the
// whole chain against a real backend — N parallel /backtest calls, N curves on the
// shared chart, N rows in the metrics table.
//
// This is also the spec that originally surfaced the _trade_markers 500
// (duplicate-timestamp label lookup) — a class of bug no MSW mock would have caught.

test.beforeEach(async ({ page }) => {
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, '1')
  }, ONBOARDING_DISMISSED_KEY)
})

test('Compare Configs page runs two real backtests and renders both curves', async ({
  page,
}) => {
  // Track any console.error or uncaught page error — the methodology-bridge slice
  // (commit 0377ee1) originally shipped a setState-in-render in the handoff
  // consumer that fired React's "Cannot update a component while rendering a
  // different component" warning. The unit tests don't exercise StrictMode so
  // this needs to be caught at the e2e layer. Any console.error during the
  // entire flow fails the test.
  const consoleErrors: string[] = []
  page.on('pageerror', (err) => consoleErrors.push(`pageerror: ${err.message}`))
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(`console.error: ${msg.text()}`)
  })

  await page.goto('/')

  await page.getByRole('button', { name: 'Compare Configs', exact: true }).click()
  await expect(page.getByRole('heading', { level: 2, name: 'Compare Configurations' })).toBeVisible()

  // Two default rows seeded from the catalog's first strategy (SMA) — Config A and
  // Config B. Tweak Config B's slow so the two requests carry distinct params; if
  // both rows are identical the chart collapses to one curve and we're not actually
  // testing fan-out.
  const configB = page.getByRole('group', { name: 'Config B' })
  const slowB = configB.getByLabel('Slow window')
  await slowB.fill('100')

  await page.getByRole('button', { name: 'Run comparison' }).click()

  // Comparison metrics table renders one row per config with the actual Sharpe etc.
  const table = page.getByRole('table', { name: 'comparison' })
  // 60s — same envelope as the single-config backtest spec: cold memory store +
  // real yfinance fetch can spend 30s+ on the first miss.
  await expect(table).toBeVisible({ timeout: 60_000 })
  // Header row + 2 data rows.
  await expect(table.locator('tr')).toHaveCount(3)

  // Comparison chart shows both rows as named series (Recharts paints each Line
  // with a name attr — assert on the legend text instead, which is more stable
  // across Recharts versions).
  const chart = page.getByRole('region', { name: 'comparison chart' })
  await expect(chart).toBeVisible()
  await expect(chart.getByText('Config A')).toBeVisible()
  await expect(chart.getByText('Config B')).toBeVisible()

  // The methodology bridge — click Validate on a Config and assert the Validation
  // page mounts with that config's (symbol, strategy) already pre-filled. This is
  // the cross-page guarantee from appShell.requestValidation.
  const validateButtons = table.getByRole('button', { name: /validate this config/i })
  await validateButtons.first().click()
  await expect(
    page.getByRole('heading', { level: 2, name: 'Validation Report' }),
  ).toBeVisible()
  // Default Compare symbol is AAPL; the catalog's first strategy is SMA.
  await expect(page.getByLabel('Symbol')).toHaveValue('AAPL')
  // 'Strategy' also matches the validation page's 'strategy info' region; scope
  // to the <select> by role to disambiguate.
  await expect(page.getByRole('combobox', { name: 'Strategy' })).toHaveValue('sma')

  // No setState-in-render warnings from the handoff path; no unrelated console
  // errors either. The fix this assertion guards: ValidationReportPage now clears
  // the store in useEffect, not during lazy-init of useState.
  expect(consoleErrors, consoleErrors.join('\n')).toEqual([])
})
