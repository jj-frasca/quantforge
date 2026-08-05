"""Equity-curve tracking (paper-trading visibility). Each paper-broker run snapshots the real
Alpaca account equity so performance is a persistent, committed time series we can actually watch --
"are we making money?" answered honestly against the $100k paper starting equity."""

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.execution.alpaca_broker import AlpacaAccount
from app.execution.equity_curve import (
    EquityPoint,
    JsonFileEquityCurve,
    append_equity_point,
)

_NOW = datetime(2026, 8, 4, tzinfo=UTC)


def _account(equity: str, cash: str = "50000") -> AlpacaAccount:
    return AlpacaAccount(equity=Decimal(equity), cash=Decimal(cash), buying_power=Decimal("200000"))


def test_append_records_the_snapshot_and_return_vs_starting_equity() -> None:
    history = append_equity_point([], _account("92488.99"), n_positions=3, now=_NOW)
    assert len(history) == 1
    pt = history[0]
    assert pt.equity == 92488.99
    assert pt.n_positions == 3
    assert pt.timestamp == _NOW
    # down 7.5% from the $100k paper start.
    assert pt.return_since_start == (92488.99 / 100000.0 - 1.0)


def test_append_uses_a_custom_starting_equity() -> None:
    history = append_equity_point(
        [], _account("110000"), n_positions=1, now=_NOW, starting_equity=100000.0
    )
    assert history[0].return_since_start == pytest.approx(0.10)  # up 10%


def test_append_is_additive_and_preserves_order() -> None:
    h1 = append_equity_point([], _account("100000"), n_positions=0, now=_NOW)
    later = datetime(2026, 8, 5, tzinfo=UTC)
    h2 = append_equity_point(h1, _account("101000"), n_positions=2, now=later)
    assert [p.equity for p in h2] == [100000.0, 101000.0]
    assert h2[-1].return_since_start == pytest.approx(0.01)


def test_json_store_round_trips_with_trailing_newline(tmp_path: Path) -> None:
    path = tmp_path / "equity_curve.json"
    store = JsonFileEquityCurve(path)
    store.save(append_equity_point(store.all(), _account("92488.99"), n_positions=3, now=_NOW))

    reloaded = JsonFileEquityCurve(path).all()
    assert len(reloaded) == 1 and reloaded[0].equity == 92488.99
    assert isinstance(reloaded[0], EquityPoint)
    assert path.read_text().endswith("\n")  # satisfies the end-of-file-fixer hook


def test_json_store_is_empty_before_first_write(tmp_path: Path) -> None:
    assert JsonFileEquityCurve(tmp_path / "absent.json").all() == []
