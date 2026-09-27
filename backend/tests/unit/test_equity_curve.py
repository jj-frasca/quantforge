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


def test_append_without_a_benchmark_leaves_alpha_unmeasured() -> None:
    # Backward-compatible default: no benchmark supplied -> both fields None (honestly "not
    # measured", never backfilled), exactly like other nullable additive fields in the codebase.
    pt = append_equity_point([], _account("95000"), n_positions=2, now=_NOW)[0]
    assert pt.benchmark_return_since_start is None
    assert pt.alpha_since_start is None


def test_append_records_benchmark_and_alpha_when_supplied() -> None:
    # The account is down 5% from $100k while the benchmark returned +1% over the same window ->
    # the honest verdict is NEGATIVE alpha of ~6 points, invisible in absolute return alone.
    # Inception equity here equals the nominal starting equity ($100k), so the book's return since
    # inception and its return since the nominal start coincide -- this case alone can't tell the
    # two apart (see the FINDING-072 regression test below for the case where they diverge).
    first = append_equity_point([], _account("100000"), n_positions=1, now=_NOW)
    later = datetime(2026, 8, 5, tzinfo=UTC)
    pt = append_equity_point(
        first, _account("95000"), n_positions=2, now=later, benchmark_return=0.01
    )[-1]
    assert pt.return_since_start == pytest.approx(-0.05)
    assert pt.benchmark_return_since_start == pytest.approx(0.01)
    assert pt.alpha_since_start == pytest.approx(-0.06)  # book -5% vs market +1% = -6% alpha


def test_alpha_is_positive_only_when_the_book_beats_the_benchmark() -> None:
    first = append_equity_point([], _account("100000"), n_positions=1, now=_NOW)
    later = datetime(2026, 8, 5, tzinfo=UTC)
    beat = append_equity_point(
        first, _account("108000"), n_positions=1, now=later, benchmark_return=0.03
    )[-1]
    assert beat.alpha_since_start == pytest.approx(0.05)  # +8% book vs +3% market = +5% alpha


def test_alpha_is_measured_since_the_benchmarks_own_inception_not_the_nominal_start() -> None:
    # Regression for FINDING-072 / ADR-141: the real book's first-ever snapshot was $92,488.99, not
    # the nominal $100k -- trading had already happened before this tracking series began. The
    # benchmark's own window starts at that first snapshot (paper_broker.py's `inception`), so alpha
    # must compare the book's return over that SAME window, not its return vs. a $100k it was never
    # actually observed at when tracking began, or the pre-tracking gap gets silently blamed on the
    # market comparison every day forever.
    first = append_equity_point([], _account("92488.99"), n_positions=3, now=_NOW)
    later = datetime(2026, 8, 6, tzinfo=UTC)
    pt = append_equity_point(
        first, _account("86050.87"), n_positions=12, now=later, benchmark_return=0.0045
    )[-1]
    book_return_since_inception = 86050.87 / 92488.99 - 1.0
    assert pt.alpha_since_start == pytest.approx(book_return_since_inception - 0.0045)
    # return_since_start is untouched -- it still honestly answers a DIFFERENT question (vs. the
    # nominal $100k paper start), just no longer conflated with the benchmark-relative alpha.
    assert pt.return_since_start == pytest.approx(86050.87 / 100000.0 - 1.0)


def test_alpha_on_the_very_first_point_is_measured_over_a_zero_length_window() -> None:
    # Degenerate case: no history yet, so the book's "return since inception" is 0 by definition
    # (this point IS the inception) -- alpha degrades to minus the benchmark's own return. This
    # combination (a benchmark supplied on the very first point) does not occur in production
    # (paper_broker.py only fetches a benchmark once >= 2 SPY bars span the inception window), but
    # the pure function should still behave sensibly if called this way.
    pt = append_equity_point(
        [], _account("108000"), n_positions=1, now=_NOW, benchmark_return=0.03
    )[0]
    assert pt.alpha_since_start == pytest.approx(-0.03)
