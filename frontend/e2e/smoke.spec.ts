import { expect, test } from '@playwright/test'

import { ONBOARDING_DISMISSED_KEY } from '../src/components/ui/OnboardingBanner'

// FAST SMOKE LAYER — the "did I break a button / blank-page / JSX-parse" check.
// Unlike backtest-flow.spec.ts this needs NO market data: it just drives the nav
// across all four pages and fails on any uncaught runtime/console error. This is
// the cheap counterpart to MSW Vitest — it proves the real bundle boots and every
// page actually mounts in a browser, which is exactly what the unclosed-JSX-fragment
// Vite parse error and the silent-form-submit regressions slipped past.

const PAGES = [
  { nav: 'Data Explorer', heading: 'Data Explorer' },
  { nav: 'Backtest Results', heading: 'Backtest Results' },
  { nav: 'Compare Configs', heading: 'Compare Configurations' },
  { nav: 'Validation', heading: 'Validation Report' },
  { nav: 'About', heading: 'About QuantForge' },
] as const

test.beforeEach(async ({ page }) => {
  await page.addInitScript((key) => {
    window.localStorage.setItem(key, '1')
  }, ONBOARDING_DISMISSED_KEY)
})

test('every page mounts with no console/page errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (err) => errors.push(`pageerror: ${err.message}`))
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(`console.error: ${msg.text()}`)
  })

  await page.goto('/')

  for (const { nav, heading } of PAGES) {
    // exact: true — otherwise "Validation" also matches the "Run validation"
    // submit button on that page (substring match), tripping strict mode.
    const navButton = page.getByRole('button', { name: nav, exact: true })
    await navButton.click()
    // The clicked nav item becomes the current page (App.tsx aria-current).
    await expect(navButton).toHaveAttribute('aria-current', 'page')
    // And the page's own <h2> renders — proves the page component actually mounted,
    // not just that the nav state flipped.
    await expect(page.getByRole('heading', { level: 2, name: heading })).toBeVisible()
  }

  expect(errors, errors.join('\n')).toEqual([])
})
