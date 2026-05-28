# ADR-002: Python 3.12 + FastAPI backend

- **Status**: Accepted
- **Date**: 2026-05-27
- **Deciders**: Joe Frasca

## Context
The backend must serve a typed REST API, run async I/O against TimescaleDB and Redis, and
host the numerical research/validation code. The language and framework should match what
quant and research-engineering teams actually use, so the project reads as production-shaped.

## Options Considered
1. **Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 (async).**
   - Pro: async-native; automatic OpenAPI docs; Pydantic gives runtime contracts that
     double as the data-quality boundary; the numerical stack (NumPy/Pandas/SciPy) is
     Python; full type hints + mypy strict.
   - Con: Python's raw throughput is lower than compiled languages (irrelevant here — this
     is research infrastructure, not low-latency execution).
2. **Python + Flask / Django REST.**
   - Pro: mature, familiar.
   - Con: async support is bolted on (Flask) or heavyweight/ORM-opinionated (Django);
     no first-class schema/OpenAPI story like Pydantic+FastAPI.
3. **A compiled backend (Go/Rust) with a separate Python compute service.**
   - Pro: raw performance.
   - Con: splits the codebase across languages; the research code is Python anyway, so
     this adds an integration seam for no benefit at this scale.

## Decision
**Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0 async.** Tooling: uv (env + deps),
ruff + black-style formatting, mypy in strict mode (CI-enforced).

## Consequences
- One language across API and research code; no cross-language seam.
- Pydantic v2 models are reused as the canonical data contracts and the quality-gate
  boundary (see ADR-004, ADR-006).
- mypy strict is enforced in CI; every function carries type annotations.
- Async routes must never make blocking DB/network calls (encoded in
  `.claude/rules/backend-python.md`).
- Performance ceiling is acceptable: this platform optimizes for research correctness and
  reproducibility, not execution latency (ADR-001 scope cuts).
