// Drive the new Compare Configs page against the running dev server and screenshot it.
// Ad-hoc agent verification (not a test): node e2e/capture-compare.mjs
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const OUT = '/tmp/qf-shots'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
await ctx.addInitScript(() => localStorage.setItem('quantforge.onboarding.dismissed', '1'))
const page = await ctx.newPage()
page.on('console', (m) => m.type() === 'error' && console.log(`CONSOLE.ERROR ${m.text()}`))
page.on('pageerror', (e) => console.log(`PAGEERROR ${e.message}`))

await page.goto(BASE_URL)
await page.getByRole('button', { name: 'Compare Configs', exact: true }).click()
await page.getByRole('heading', { name: /compare configurations/i }).waitFor()
await page.screenshot({ path: `${OUT}/compare-initial.png`, fullPage: true })
console.log('SHOT compare-initial.png')

// Differentiate the two seeded rows so the comparison is meaningful, then run it.
const slows = page.getByLabel(/slow/i)
const count = await slows.count()
console.log(`slow inputs found: ${count}`)
if (count >= 2) {
  await slows.nth(1).fill('100')
}
await page.getByRole('button', { name: /run comparison/i }).click()

// Wait for the comparison table to render (real backend → yfinance → N backtests).
await page.getByRole('table', { name: /comparison/i }).waitFor({ state: 'visible', timeout: 90_000 })
await page.waitForTimeout(800)
await page.screenshot({ path: `${OUT}/compare-result.png`, fullPage: true })
console.log('SHOT compare-result.png')

await browser.close()
console.log('DONE')
