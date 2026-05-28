---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend TypeScript Conventions

Applies when editing any TS/TSX under `frontend/`. Behavioral rules live in CLAUDE.md; domain
knowledge in the frontend-engineer agent.

- **Strict typing**: TS strict mode. No `any`; no `@ts-ignore`/`@ts-expect-error` without a
  one-line cited reason. Prefer discriminated unions over optional-field soup.
- **Validate at the network boundary**: every API response is parsed with a **Zod** schema in
  `src/services/`. Components receive already-validated, typed data — never raw `fetch` JSON.
- **Server state = Tanstack Query**, one hook per endpoint. Do NOT fetch in `useEffect`. Always
  handle loading / empty / error states (a missing error state is a bug).
- **Client state = Zustand**. No prop-drilling for cross-cutting UI state.
- **Components**: functional + hooks; small and focused; co-locate a component with its test.
- **Tests**: Vitest + React Testing Library; mock the API with **MSW** (no real network). Assert
  on what the user sees (rendered text/roles), not implementation details. Coverage ≥ 75%.
- **Charts**: Recharts for equity curves / distributions.
- **Honesty in UI**: a failing ValidationReport (high PBO, DSR ≤ 0) must render as a clear
  "does not pass" with flags surfaced — never visually buried (mirrors CLAUDE.md rule 6 intent).
