## Session: Implement [METHOD /path] Endpoint

**Agent to invoke**: none (read research-expert/data-engineer if the handler touches their domain)
**Cold memory to read first**: .claude/context/api-contracts.md

**Entry criteria**:
- [ ] The domain logic this endpoint exposes already exists and is tested
- [ ] Request/response Pydantic schemas defined (or part of this task)
- [ ] All previous tests passing

**Today's task**:
Implement [METHOD /api/v1/path] in backend/app/api/v1/[module].py.

[1–3 sentences: what it returns, which service/component it calls]
Request model: [name]. Response model: [name]. Versioned under /api/v1.

**Files to read first**:
- backend/app/api/v1/ (existing endpoint for the router pattern)
- the service/component the handler will call
- .claude/context/api-contracts.md (the contract for this endpoint)

**Start in plan mode**: confirm the request/response schemas and the dependency wiring
(app/dependencies.py), propose the handler before writing code.

**Exit criteria**:
- [ ] Endpoint is async; NO sync/blocking DB calls in the route (CLAUDE.md)
- [ ] Request + response validated by Pydantic models
- [ ] Tests via httpx/TestClient: happy path, validation error (422), not-found/error paths
- [ ] OpenAPI docs render correctly (response_model set)
- [ ] Coverage gate met; mypy strict clean
- [ ] Commit follows COMMIT_TEMPLATE.md
