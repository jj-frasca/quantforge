// Agent eyes on the EquityCurvePanel headline. Drives the running dev server against the REAL
// backend (serving data/equity_curve.json) and screenshots the Discoveries page top. Prints console
// errors/pageerrors.
//   node e2e/capture-equity-curve.mjs --out /tmp/qf-shots
import { chromium } from '@playwright/test'
import { mkdirSync } from 'node:fs'

const BASE_URL = process.env.BASE_URL ?? 'http://localhost:5173'
const outArg = process.argv.indexOf('--out')
const OUT = outArg !== -1 ? process.argv[outArg + 1] : '/tmp/qf-shots'
mkdirSync(OUT, { recursive: true })
const ONBOARDING_KEY = 'quantforge.onboarding.dismissed'

const browser = await chromium.launch()
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } })
await ctx.addInitScript((key) => window.localStorage.setItem(key, '1'), ONBOARDING_KEY)
const page = await ctx.newPage()
page.on('console', (m) => m.type() === 'error' && console.log(`CONSOLE.ERROR ${m.text()}`))
page.on('pageerror', (e) => console.log(`PAGEERROR ${e.message}`))

await page.goto(BASE_URL)
await page.getByRole('button', { name: 'Discoveries', exact: true }).click()
await page.getByLabel('equity curve section').waitFor({ state: 'visible', timeout: 30_000 })
// Assert the real seeded snapshot rendered as the headline (not the empty/loading state).
const equity = page.getByText('$92,488.99')
await equity.waitFor({ state: 'visible', timeout: 30_000 })
console.log(`HEADLINE_EQUITY ${await equity.textContent()}`)
console.log(`RETURN ${await page.getByText(/since \$100k start/).textContent()}`)
await page.waitForTimeout(500)
const path = `${OUT}/equity-curve.png`
await page.screenshot({ path, fullPage: true })
console.log(`SHOT ${path}`)

await browser.close()
console.log('DONE')
