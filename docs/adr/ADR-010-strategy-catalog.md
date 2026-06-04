# ADR-010: Schema-driven strategy catalog

- **Status**: Accepted
- **Date**: 2026-06-03
- **Deciders**: Joe Frasca

## Context
Through 5 backtest endpoints, 3 frontend pages, and the first 3 strategies (SMA, momentum,
mean reversion), each strategy lived in **three places** that had to be kept in sync by hand:

1. A `BaseStrategy` subclass under `backend/app/research/strategies/` (algorithm).
2. A Pydantic config variant inside the `StrategyConfig` discriminated union in
   `backend/app/api/v1/backtest.py` (API contract).
3. A hardcoded branch in the frontend `StrategyParamFields` component plus matching TS types
   in `frontend/src/types/backtest.ts` (UI form).

Adding a strategy meant editing all three. The frontend branch in particular hardcoded
labels (`"Fast"`, `"Slow"`, `"Lookback"`, ...) and per-strategy onChange handlers — adding
a strategy required new TS, a new sub-component branch, and updated tests.

Joe explicitly flagged this as the wrong shape: *"right now it just looks like we have 3
strategies and can pick a symbol but that isn't nearly complex enough"*. A research
platform needs strategy expansion to be **cheap** so the rigor (PBO, DSR, walk-forward)
gets applied to a real variety of methods, not three tutorial-grade configs.

## Options Considered
1. **Hand-rolled per-strategy frontend code** (status quo).
   - Pro: simplest; no abstraction overhead.
   - Con: scales linearly with # of strategies — 10 strategies = 10 sub-components, 10
     TS types, 10 test fixtures. Discourages experimenting with new strategies.

2. **Pydantic's auto-generated JSON Schema** as the wire format
   (`StrategyConfig.model_json_schema()`).
   - Pro: zero duplication; the schema *is* the Pydantic model.
   - Con: JSON Schema is verbose (`$defs`, `oneOf`, `discriminator`) and lacks the
     UI-specific fields a form needs (human label, description, step, citations); we'd
     have to add `json_schema_extra` for each, which is the same duplication in a less
     readable package. Also couples the public API to Pydantic's emitted shape — any
     Pydantic upgrade can subtly shift it.

3. **Strategy composition / a small DSL** (let users combine primitives like
   `SMA(20,50) > 0 AND ATR < X`).
   - Pro: highest ceiling — closer to a real research platform.
   - Con: big build; a half-finished DSL reads worse than 10 well-tested named strategies.
     Right move for *later*, not for the next step.

4. **A purpose-built strategy catalog** exposed via `GET /api/v1/strategies` —
   `list[StrategySchema]` where each entry has `name`, `label`, `description`,
   `citations`, and a flat `list[ParamSchema]` (with `type`, `default`, `min`, `max`,
   `step`, `label`, `description`). The frontend renders dropdown options + the param
   form by iterating the catalog.
   - Pro: adding a strategy becomes a **backend-only** change (Pydantic config + catalog
     entry + dispatch line); the frontend lights up automatically. Catalog carries
     research metadata (citations) that pure JSON Schema doesn't have a natural place
     for. A consistency unit test guards against the catalog drifting from the Pydantic
     config.
   - Con: a small amount of duplication between the catalog entry's param `name` and the
     Pydantic field name. Mitigated by the consistency test (CI fails on drift).

## Decision
**Option 4 — a purpose-built catalog at `app/research/strategies/catalog.py`, served by
`GET /api/v1/strategies`.**

The frontend has a single `<StrategyParamForm>` that maps over `ParamSchema[]` and renders
one labelled numeric input per parameter (respecting `type`, `min`, `max`, `step`).
`useStrategies()` (Tanstack `useQuery` with `staleTime: Infinity`) caches the catalog for
the session. Both Backtest Results and Validation Report consume the same hook.

We chose Option 4 over Option 2 (JSON Schema) because the catalog explicitly carries the
UI labels, descriptions, citations, and rendering hints we actually need; emitting all
that through `json_schema_extra` would have been the same data, just buried in a less
ergonomic shape and coupled to Pydantic's internal schema-emission rules.

## Consequences

- **Adding a strategy** is now a 5-line diff: a `BaseStrategy` subclass, a Pydantic
  config variant, a dispatch line in `_build_strategy()`, a catalog entry, and an entry
  in `_CONFIG_FOR_NAME` in the consistency test. **Zero frontend code, zero TS types,
  zero frontend test changes** — the catalog ships the labels and the consistency test
  catches drift. (This was demonstrated by ADR-010's first three follow-on commits adding
  RSI Mean Reversion, Donchian Channel Breakout, and Bollinger Bands — all backend-only
  diffs.)

- **`backend/tests/unit/test_strategy_catalog_consistency.py` is load-bearing.** Three
  assertions: every catalog name has a Pydantic config; every catalog entry's param
  names == its config's field names; every catalog default round-trips through Pydantic
  validation. If any of these breaks in CI, the catalog has drifted from the API contract
  and the frontend form will silently misbehave.

- **The frontend Zod schema for the strategy is INTENTIONALLY loose:**
  `z.object({ name: z.string().min(1) }).passthrough()` — non-empty name plus any extra
  fields. The backend catalog (this ADR) + the Pydantic `StrategyConfig` discriminated
  union are the single source of truth for the *list of valid names* and the *per-name
  parameter shapes*. The frontend used to mirror that union as a Zod discriminated
  union, which became a *hidden shadow validator*: every new strategy added to the
  catalog silently failed the submit-time `.parse()` because the frontend's three-
  variant union didn't know about it. Recorded as
  [[feedback-frontend-shadow-validators]]. The lesson: **never re-validate at the
  frontend a constraint that lives on the backend.** Validate only what the frontend
  uniquely owns (non-empty name + numeric inputs from the form).

- **Strategy composition / a DSL is now an easier next step**, not a harder one. A
  composed strategy could ship as `name="composed"` with a `parameters` list of "sub-
  strategy" references; the same form-rendering machinery would handle it.

- **The `frontend/src/features/strategy-config/` directory is now formally unnecessary**
  for parameter selection — Backtest Results already takes per-strategy params via the
  catalog-driven form. The dir is kept empty for now in case we repurpose it as a
  "compare configs overlaid" page (which is the next natural use of `/backtest`).

## Pattern for adding a strategy
1. Subclass `BaseStrategy` under `backend/app/research/strategies/<name>.py` — implement
   `generate_signals(data)`, set `name` + `research_citations` + `parameters`. Honor the
   "no look-ahead" contract (`shift(1)` or trailing rolling windows).
2. Add a Pydantic config variant in `app/api/v1/backtest.py` (`<Name>Config`,
   `name: Literal["..."]`, `Field(default=..., ge=..., gt=...)`).
3. Append the variant to the `StrategyConfig` union.
4. Add a dispatch line in `_build_strategy()`.
5. Add a `StrategySchema(...)` entry to `STRATEGY_CATALOG` in
   `app/research/strategies/catalog.py`. The param `name`s **must** match the Pydantic
   field names.
6. Add the config class to `_CONFIG_FOR_NAME` in
   `tests/unit/test_strategy_catalog_consistency.py`.
7. Write unit tests for the algorithm (param rejection, signal orientation on synthetic
   data, no look-ahead behavior).
8. Write an integration test in `tests/integration/test_backtest_endpoint.py` exercising
   the new variant.

CLAUDE.md rule 1 (test first) and rule 2 (one logical unit per commit) apply unchanged.
