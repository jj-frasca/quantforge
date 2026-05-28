---
name: tdd-cycle
description: >
  Run the red-green TDD loop for a new QuantForge function/class — write the failing
  test first, confirm RED, implement minimally, confirm GREEN, add edge/error +
  Hypothesis property tests, check coverage. Use whenever adding backend behavior.
---

# tdd-cycle

Guides the non-negotiable TDD loop (CLAUDE.md rule 1) and actually runs the tests at
each gate, rather than leaving it to memory.

## Procedure
1. **RED — write the test first.**
   - Name it `test_<unit>_<scenario>_<expected_outcome>` (see `.claude/rules/test-files.md`).
   - Cover the happy path to start. Put it in `backend/tests/unit/` (or `integration/`).
2. **Confirm it fails for the right reason.**
   - `cd backend && uv run pytest tests/path::test_name -x`
   - It must FAIL (missing impl / wrong result) — not error on a typo or bad import.
3. **GREEN — implement the minimum** to pass. No speculative extras (CLAUDE.md scope rules).
4. **Confirm it passes.** Re-run the same test.
5. **Expand coverage** — add edge cases and error paths as separate tests:
   - boundary values, empty/degenerate inputs, the documented `raises` paths.
6. **Property test for financial math.** If the unit computes a financial quantity, add a
   Hypothesis test for its invariant (ARCHITECTURE.md §8): e.g. PBO ∈ [0,1],
   DSR ≤ observed Sharpe, max drawdown ∈ [-1,0], signals ∈ [-1,1], costs reduce returns.
7. **Gate** — `make test` (synthetic only) must pass AND coverage stays ≥ 85%
   (`--cov-fail-under` enforces it). Then `make lint` (ruff + mypy strict).
8. Hand off to **commit-writer** — production code + its tests commit together.

## Reminders
- A test that passes before the implementation exists is not a TDD test — make it fail first.
- Tests must be deterministic: no live network (mark `@pytest.mark.live` if unavoidable),
  seed RNGs, use the synthetic fixtures.
- Don't lower the coverage gate to make a commit pass — add the missing test.
