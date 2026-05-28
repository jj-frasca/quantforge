# Session Playbooks

These are what you paste into Claude Code at the start of a session. Short, specific,
scoped. The persistent three-tier context (CLAUDE.md + agents + cold memory) handles
everything else.

How to use:

1. Choose the playbook for your task type.
2. Copy it. Fill in the [BRACKETED] sections.
3. Paste into Claude Code at session start.
4. Use plan mode first (Shift+Tab x2 or /plan).
5. Review the plan before implementing.
6. Do not start the next playbook until the current one is committed and passing.

One playbook = one vertical feature slice. If a session is running long or touching more
than ~15 files, stop, commit what works, start a new session.

| Playbook | For |
|---|---|
| `new-component.md` | Generic: implement a new class/function |
| `new-adapter.md` | Data layer: add a new data source |
| `new-strategy.md` | Research: add a new trading strategy |
| `new-validator.md` | Validation: add a new validation component |
| `new-endpoint.md` | API: add a new FastAPI endpoint |
| `new-frontend-feature.md` | Frontend: add a new page/component (Phase 5+) |
| `debug-failing-tests.md` | Recovery: diagnose and fix test failures |
