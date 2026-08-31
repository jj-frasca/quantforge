/// <reference types="vitest/config" />
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Dev: forward /api to the local FastAPI backend so the SPA is same-origin.
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    // Vitest defaults the fork pool to the LOGICAL core count. On an 8-physical/16-logical
    // machine that is 16 jsdom environments against 8 cores, and it is slower as well as
    // flakier: measured on this suite, 16 forks took 74s and timed out the heaviest test
    // (8 sequential userEvent clicks, 0.9s when it runs alone, >5s under that load), while
    // 6 forks took 52s and passed everything. CI has fewer cores than this cap, so it is a
    // no-op there. Override with VITEST_MAX_WORKERS when a machine wants something else.
    maxWorkers: Number(process.env.VITEST_MAX_WORKERS ?? 6),
    // Vitest's default per-test budget is 5,000ms of WALL CLOCK, which on a shared machine
    // measures the scheduler rather than the code. Two different tests have now timed out
    // here — one takes 929ms alone, the other ~50ms — while a peer checkout ran its own
    // suite. 15s still fails a genuinely hung test by two orders of magnitude.
    // NOT the fix for a slow test: FINDING-014's backend case was real slowness (one
    // `iterrows()`, 69x) and raising a timeout there would have hidden it. Measure which
    // one you have before touching this number.
    testTimeout: 15_000,
    // Vitest owns src/** only. The Playwright e2e specs in e2e/** import
    // @playwright/test and must NOT be collected here (they fail to load under
    // Vitest's runner).
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
    exclude: ['e2e/**', 'node_modules/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/**/*.test.{ts,tsx}',
        'src/test/**',
        'src/vite-env.d.ts',
      ],
      thresholds: { lines: 75, functions: 75, branches: 75, statements: 75 },
    },
  },
})
