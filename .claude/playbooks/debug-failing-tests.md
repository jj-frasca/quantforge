## Session: Diagnose and fix failing tests

**Agent to invoke**: the domain agent for the failing area (data-engineer / research-expert)
**Cold memory to read first**: the context doc for the failing subsystem

**Entry criteria**:
- [ ] You can reproduce the failure locally (`make test` or a targeted pytest run)
- [ ] You are on a clean tree or have stashed unrelated work

**Today's task**:
Get the suite green again WITHOUT weakening the tests or the coverage gate.

**Procedure (start in plan mode — diagnose before changing anything)**:
1. Reproduce: `cd backend && uv run pytest <path> -x -ra` (or full `make test`).
2. Read the failure: assertion vs error vs collection error. Read the FULL traceback.
3. Form a hypothesis about the ROOT CAUSE — is the test wrong, or the code?
   - Test wrong → fix the test only if the spec/contract says so (cite it).
   - Code wrong → fix the code; the test stays as the source of truth.
4. Max 2 fix attempts per failure (CLAUDE.md). After 2, STOP and explain the root cause.
5. Re-run the targeted test, then the full `make check`.

**Hard rules**:
- NEVER delete/skip/xfail a test to make the suite pass without explicit approval and a
  written reason.
- NEVER lower `--cov-fail-under` or relax markers to dodge the gate.
- NEVER `--no-verify` past a hook. Fix the cause.
- For financial-math failures, suspect the engine first — a broken invariant (drawdown > 0,
  PBO outside [0,1]) means the calculation is wrong, not the test.

**Exit criteria**:
- [ ] Root cause identified and stated
- [ ] `make check` green (lint + tests + coverage)
- [ ] No tests weakened/skipped to get there
- [ ] Commit follows COMMIT_TEMPLATE.md (type: fix)
