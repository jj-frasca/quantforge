"""get_repository(): routed by Settings.storage_backend. `memory` (default) returns
an InMemoryPriceBarRepository — what makes standalone `uvicorn` work without Docker;
the singleton survives across requests within a process. The `timescale` branch is
exercised by the Docker-only integration tests."""

import pytest

from app.config import get_settings
from app.data.storage.memory import InMemoryPriceBarRepository
from app.dependencies import _memory_repository, get_repository


@pytest.fixture(autouse=True)
def _reset_caches() -> None:
    # Settings are lru_cache'd app-wide; reset between tests so changing storage_backend
    # in one test doesn't leak into the next, and so the memory repo gets a fresh state.
    get_settings.cache_clear()
    _memory_repository.cache_clear()


def test_get_repository_returns_in_memory_when_storage_backend_is_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    repo = get_repository()
    assert isinstance(repo, InMemoryPriceBarRepository)


def test_get_repository_returns_the_same_memory_singleton_across_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Process-local cache so bars ingested by one request survive to the next within
    # one uvicorn process (restart drops them — that's the dev tradeoff).
    monkeypatch.setenv("STORAGE_BACKEND", "memory")
    assert get_repository() is get_repository()


def test_default_storage_backend_is_memory_so_uvicorn_just_works(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # The default must be `memory`, not `timescale`. CLAUDE.md rule 8 / .env.example flow:
    # `make dev` sets STORAGE_BACKEND=timescale via docker-compose, but a fresh
    # `uv run uvicorn app.main:app` has no env override and must not try to connect.
    monkeypatch.delenv("STORAGE_BACKEND", raising=False)
    assert get_settings().storage_backend == "memory"
    assert isinstance(get_repository(), InMemoryPriceBarRepository)
