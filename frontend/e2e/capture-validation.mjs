// Verify the "honest loser" thesis end-to-end: run the Triple-MA-on-QQQ config through
// the full validation suite (PBO / Deflated Sharpe / walk-forward / purged CV) and confirm
// the UI renders a clear "does not pass" with flags — not a buried failure (CLAUDE.md rule 6).
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const OUT = '/tmp/qf-shots'
mkdirSync(OUT, { recursive: true })

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 1000 } })
await ctx.addInitScript(() => localStorage.setItem('quantforge.onboarding.dismissed', '1'))
const page = await ctx.newPage()
page.on('console', (m) => m.type() === 'error' && console.log(`CONSOLE.ERROR ${m.text()}`))
page.on('pageerror', (e) => console.log(`PAGEERROR ${e.message}`))

await page.goto('http://localhost:5173')
await page.getByRole('button', { name: 'Validation', exact: true }).click()
await page.getByLabel('Symbol').fill('QQQ')
await page.getByRole('combobox', { name: 'Strategy' }).selectOption('triple_ma_alignment')
await page.getByRole('button', { name: /run validation/i }).click()

const report = page.getByRole('region', { name: 'validation report' })
await report.waitFor({ state: 'visible', timeout: 150_000 })
await page.waitForTimeout(500)
const verdict = (await page.getByRole('status').textContent())?.trim()
console.log(`VERDICT: ${verdict}`)
await page.screenshot({ path: `${OUT}/validation-honest-loser.png`, fullPage: true })
console.log('SHOT validation-honest-loser.png')
await browser.close()
console.log('DONE')
