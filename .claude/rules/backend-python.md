---
paths:
  - backend/**/*.py
---

# Backend Python Conventions

Applies when editing any Python under `backend/`. These are file-type conventions;
behavioral rules live in CLAUDE.md, domain knowledge in the agent specs.

- **Typing**: full annotations on every function (mypy strict, enforced in CI). No bare
  `Any`. Prefer `X | None` over `Optional[X]`. No untyped `def`.
- **Async discipline**: never make sync/blocking DB or network calls inside `async`
  routes. Use SQLAlchemy 2.0 async + async drivers. Blocking work → `run_in_executor`.
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
