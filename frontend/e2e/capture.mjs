// Agent "eyes" on the frontend. Drives the RUNNING dev server (npm run dev) with a
// real Chromium and writes screenshots an agent can read back — the interactive
// counterpart to the canned specs. NOT a test: no assertions, no webServer; it
// assumes the app is already up at BASE_URL.
//
//   node e2e/capture.mjs                       # all pages, default flow
//   node e2e/capture.mjs --out /tmp/qf-shots   # custom output dir
//
// Output: one PNG per page + one for the backtest result, into OUT (default
// /tmp/qf-shots). Prints each path so the agent knows what to read.
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const outArg = process.argv.indexOf('--out')
const OUT = outArg !== -1 ? process.argv[outArg + 1] : '/tmp/qf-shots'
mkdirSync(OUT, { recursive: true })

const ONBOARDING_KEY = 'quantforge.onboarding.dismissed'

const shot = async (page, name) => {
  const path = `${OUT}/${name}.png`
  await page.screenshot({ path, fullPage: true })
  console.log(`SHOT ${path}`)
}

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript((key) => window.localStorage.setItem(key, '1'), ONBOARDING_KEY)
const page = await ctx.newPage()
page.on('console', (m) => m.type() === 'error' && console.log(`CONSOLE.ERROR ${m.text()}`))
page.on('pageerror', (e) => console.log(`PAGEERROR ${e.message}`))

await page.goto(BASE_URL)

for (const [nav, name] of [
  ['Data Explorer', 'data-explorer'],
  ['Backtest Results', 'backtest-results'],
  ['Validation', 'validation'],
  ['About', 'about'],
]) {
  await page.getByRole('button', { name: nav, exact: true }).click()
  await page.waitForTimeout(300)
  await shot(page, name)
}

// Drive the real backtest flow end-to-end and capture the rendered chart.
await page.getByRole('button', { name: 'Backtest Results', exact: true }).click()
await page
  .getByRole('article', { name: 'SMA crossover on SPY' })
  .getByRole('button', { name: 'Load this preset' })
  .click()
await page.getByRole('button', { name: 'Run backtest' }).click()
await page
  .getByRole('region', { name: 'equity curve' })
  .waitFor({ state: 'visible', timeout: 60_000 })
await page.waitForTimeout(500)
await shot(page, 'backtest-result')

await browser.close()
console.log('DONE')
