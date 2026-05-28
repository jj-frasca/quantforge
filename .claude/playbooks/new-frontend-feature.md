## Session: Implement [FEATURE/PAGE NAME]

**Phase**: 5+ (frontend)
**Agent to invoke**: frontend-engineer
**Cold memory to read first**: .claude/context/api-contracts.md

**Entry criteria**:
- [ ] The backend endpoint(s) this feature consumes exist and are tested
- [ ] frontend-engineer agent spec written; frontend-typescript rules in place
- [ ] All previous tests passing (frontend coverage gate ≥ 75%)

**Today's task**:
Implement [FEATURE/PAGE NAME] under frontend/src/features/[feature]/.

[2–4 sentences: what the user sees/does, which API data it renders]
Note: ValidationReport is the highest-priority page (~70% of frontend effort) — match that
bar for data density and clarity. Dark mode, professional, data-dense.

**Files to read first**:
- an existing feature under frontend/src/features/ for the pattern
- frontend/src/services/ (API client) and frontend/src/types/ (shared types)
- the relevant section of .claude/context/api-contracts.md

**Start in plan mode**: confirm the Zod schema for the API response, the Tanstack Query
hook, and the component breakdown before writing code.

**Exit criteria**:
- [ ] API responses validated at runtime with Zod
- [ ] Server state via Tanstack Query; client state via Zustand (no prop-drilling)
- [ ] Vitest + RTL tests; API mocked with MSW (no real network)
- [ ] Loading / empty / error states handled
- [ ] Frontend coverage gate met (≥ 75%)
- [ ] Commit follows COMMIT_TEMPLATE.md
