"""ADR-414: HISTORY_START env var resolution for the cross-sectional hunt driver. A universe file
alone only changes which symbols are hunted, not how far back their history is fetched -- this is
the independent mechanism that actually extends the panel."""

from datetime import UTC, datetime

import pytest
from scripts.cross_sectional_hunt import _resolve_history_start

from app.research.lab.history import RECENT_HISTORY_START


def test_resolve_history_start_defaults_to_recent_history_start_when_unset() -> None:
    assert _resolve_history_start({}) == RECENT_HISTORY_START


def test_resolve_history_start_defaults_when_env_var_is_empty_string() -> None:
    assert _resolve_history_start({"HISTORY_START": ""}) == RECENT_HISTORY_START


def test_resolve_history_start_honors_an_explicit_override() -> None:
    assert _resolve_history_start({"HISTORY_START": "1990-01-01"}) == datetime(
        1990, 1, 1, tzinfo=UTC
    )


def test_resolve_history_start_rejects_an_unparseable_override() -> None:
    with pytest.raises(ValueError):
        _resolve_history_start({"HISTORY_START": "not-a-date"})
