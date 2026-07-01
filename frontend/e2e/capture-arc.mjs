// Methodology-arc demo, end-to-end in a real browser:
//   Backtest Results → "Triple MA alignment on QQQ" preset → Run backtest →
//   "Validate this strategy →" bridge → (form pre-filled by handoff) →
//   Run validation → regime breakdown + "does not pass" verdict.
//
// This is the LOAD-BEARING demo (the "honest loser"): the existing
// capture-validation.mjs jumps straight to the Validation page, so it never
// exercises the Compare/Backtest → Validate handoff. This script does, and
// collects console.error/pageerror across the WHOLE flow (the setState-in-render
// class of bug only fires during the cross-page handoff).
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

// 1. Backtest Results → load the honest-loser preset
await page.getByRole('button', { name: 'Backtest Results', exact: true }).click()
const card = page.getByRole('article', { name: 'Triple MA alignment on QQQ' })
await card.getByRole('button', { name: 'Load this preset' }).click()
if ((await page.getByLabel('Symbol').inputValue()) !== 'QQQ') throw new Error('preset did not fill QQQ')

// 2. Run the backtest, wait for the real equity curve
await page.getByRole('button', { name: 'Run backtest' }).click()
const equity = page.getByRole('region', { name: 'equity curve' })
await equity.waitFor({ state: 'visible', timeout: 120_000 })
await page.waitForTimeout(400)
await page.screenshot({ path: `${OUT}/arc-1-backtest.png`, fullPage: true })
console.log('SHOT arc-1-backtest.png')

// 3. Cross the bridge: "Validate this strategy →"
await page.getByRole('button', { name: 'Validate this strategy →' }).click()

// 4. Handoff should have pre-filled the validation form
const sym = await page.getByLabel('Symbol').inputValue()
const strat = await page.getByRole('combobox', { name: 'Strategy' }).inputValue()
console.log(`HANDOFF prefill: symbol=${sym} strategy=${strat}`)
if (sym !== 'QQQ' || strat !== 'triple_ma_alignment') throw new Error('handoff did not pre-fill the validation form')

// 5. Run validation → regime breakdown + verdict
await page.getByRole('button', { name: /run validation/i }).click()
const report = page.getByRole('region', { name: 'validation report' })
await report.waitFor({ state: 'visible', timeout: 150_000 })
await page.waitForTimeout(500)
const verdict = (await page.getByRole('status').textContent())?.trim()
console.log(`VERDICT: ${verdict}`)
await page.screenshot({ path: `${OUT}/arc-2-validation.png`, fullPage: true })
console.log('SHOT arc-2-validation.png')

await browser.close()
console.log(errors.length ? `FAIL: ${errors.length} console/page error(s)` : 'CLEAN: no console/page errors across the arc')
console.log('DONE')
