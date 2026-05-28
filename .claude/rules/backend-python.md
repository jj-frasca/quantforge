---
paths:
  - backend/**/*.py
---

# Backend Python Conventions

Applies when editing any Python under `backend/`. These are file-type conventions;
behavioral rules live in CLAUDE.md, domain knowledge in the agent specs.

- **Typing**: full annotations on every function (mypy strict, enforced in CI). No bare
  `Any`. Prefer `X | None` over `Optional[X]`. No untyped `def`.
- **DB access is synchronous (ADR-009)**: SQLAlchemy 2.0 *sync* engine/sessions on the
  `psycopg` (psycopg3) driver. Prefer sync `def` FastAPI routes for DB/blocking work — FastAPI
  runs them in a threadpool, so they never stall the event loop. NEVER call a blocking driver
  inside an `async def` route (that is worse than a plain `def`). Not asyncpg; not psycopg2.
- **Money & prices**: use `Decimal`, never `float`, for prices/financial quantities that
  must round-trip exactly (PriceBar OHLC, adj_factor). `float` is fine for derived stats.
- **Config**: all settings flow through `app/config.py` (Pydantic Settings). Never read
  `os.environ` directly in business code; never hardcode secrets or connection strings.
- **Validation at boundaries**: validate external/untrusted input with Pydantic models.
  Trust internal calls — don't re-validate what a typed internal contract already guarantees.
- **Imports**: absolute imports from `app.` (e.g. `from app.data.models import PriceBar`).
- **Docstrings**: short. Add a `Notes:` section only when a decision is non-obvious
  (a constraint, an invariant, a workaround). No multi-paragraph docstrings.
- **Data-quality honesty**: in any quality-check code/docstring, write "flags potential X",
  never "prevents/guarantees X" (CLAUDE.md rule 6).
