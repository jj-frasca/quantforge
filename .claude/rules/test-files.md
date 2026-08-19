---
paths:
  - "**/test_*.py"
  - "**/*_test.py"
  - "**/*.test.ts"
  - "**/*.test.tsx"
---

# Test File Conventions

Applies when editing any test file. TDD is non-negotiable (CLAUDE.md rule 1): the test
is written first and must FAIL before the implementation exists.

- **Naming**: `test_<unit>_<scenario>_<expected_outcome>`.
  e.g. `test_ohlcv_normalizer_given_negative_price_raises_validation_error`.
- **Coverage per public function**: happy path + edge cases + error paths.
- **Financial-math invariants → Hypothesis property tests** (not just examples). The
  required invariants are listed in ARCHITECTURE.md §8 (PBO ∈ [0,1], DSR ≤ observed
  Sharpe, max drawdown ∈ [-1,0], signals ∈ [-1,1], costs always reduce returns, …).
- **Markers**: tag tests that hit a live external source (e.g. live yfinance) with
  `@pytest.mark.live` so CI excludes them. Use `integration` / `e2e` markers as fitting.
- **Order-independence (ADR-040)**: `make test` runs with `pytest-xdist -n auto`, so tests
  execute in parallel in an arbitrary order. Never write a fixed path (use `tmp_path`),
  never mutate module state, never depend on another test having run first. If a test fails
  only under `-n auto`, reproduce with `-n 0` and fix the shared state — do not pin the test.
- **Determinism**: no real network or wall-clock in the standard suite. Seed RNGs.
  Use the synthetic fixtures in `backend/tests/fixtures/synthetic/` for data-shaped tests.
- **Backtest oracle tests** (ARCHITECTURE.md §8) must pass before any validation test is
  meaningful — a sophisticated statistic on a buggy engine is worthless.
- Production code and its tests are committed together (CLAUDE.md rule 2).
