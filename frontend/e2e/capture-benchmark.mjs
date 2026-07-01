// ADR-013 visual check: run a real backtest (Triple-MA on QQQ, a non-SPY symbol so the
// SPY benchmark is genuinely fetched) and confirm the vs-SPY panel renders below the equity
// curve with alpha/beta/IR. Collects console/page errors across the run.
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const OUT = '/tmp/qf-shots'
mkdirSync(OUT, { recursive: true })

const errors = []
const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
await ctx.addInitScript(() => localStorage.setItem('quantforge.onboarding.dismissed', '1'))
const page = await ctx.newPage()
page.on('console', (m) => {
  if (m.type() === 'error') { errors.push(m.text()); console.log(`CONSOLE.ERROR ${m.text()}`) }
})
page.on('pageerror', (e) => { errors.push(e.message); console.log(`PAGEERROR ${e.message}`) })

await page.goto('http://localhost:5173')
await page.getByRole('button', { name: 'Backtest Results', exact: true }).click()
await page.getByRole('article', { name: 'Triple MA alignment on QQQ' })
  .getByRole('button', { name: 'Load this preset' }).click()
await page.getByRole('button', { name: 'Run backtest' }).click()

const equity = page.getByRole('region', { name: 'equity curve' })
await equity.waitFor({ state: 'visible', timeout: 120_000 })

const bench = page.getByRole('region', { name: 'benchmark comparison' })
await bench.waitFor({ state: 'visible', timeout: 15_000 })
const verdict = (await bench.getByRole('status').textContent())?.trim()
console.log(`BENCHMARK VERDICT: ${verdict}`)

await bench.scrollIntoViewIfNeeded()
await page.waitForTimeout(300)
await page.screenshot({ path: `${OUT}/benchmark-panel.png`, fullPage: true })
console.log('SHOT benchmark-panel.png')

await browser.close()
console.log(errors.length ? `FAIL: ${errors.length} console/page error(s)` : 'CLEAN: no console/page errors')
console.log('DONE')
