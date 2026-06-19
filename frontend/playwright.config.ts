import { defineConfig, devices } from '@playwright/test'

// E2E smoke layer (separate from Vitest unit tests in src/**).
// These hit a REAL backend + REAL dev server — they catch the class of bugs
// MSW-mocked Vitest cannot: dev-server wiring, real CSS layout at a real
// viewport, and "did the user flow actually end in a rendered chart".
//
// webServer blocks start both processes and waits for them to be reachable.
// The backend defaults to STORAGE_BACKEND=memory and lazily fetches yfinance
// on a cache miss, so no Docker is required. First run pulls real bars over
// the network, hence the generous per-test timeout.
export default defineConfig({
  testDir: './e2e',
  // Generous: the data-backed flow re-fetches from yfinance on every run (memory
  // store starts cold) and yfinance throttles under repeated local runs, so the
  // first real fetch can take 30s+. The fast smoke test is unaffected by this.
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list'], ['json', { outputFile: 'e2e-report.json' }]],
  use: {
    baseURL: 'http://localhost:5173',
    viewport: { width: 1280, height: 900 },
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command:
        'cd ../backend && STORAGE_BACKEND=memory uv run uvicorn app.main:app --host 127.0.0.1 --port 8000',
      url: 'http://127.0.0.1:8000/health',
      timeout: 60_000,
      reuseExistingServer: true,
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      timeout: 60_000,
      reuseExistingServer: true,
    },
  ],
})
