"""Intrinsic validity and write prevalidation for observed account evidence (ADR-169)."""

from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.execution.alpaca_broker import AlpacaAccount
from app.execution.equity_curve import EquityPoint, JsonFileEquityCurve, append_equity_point

_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _payload() -> dict[str, object]:
    return {
        "timestamp": _NOW,
        "equity": 100000.0,
        "cash": 1000.0,
        "n_positions": 1,
        "return_since_start": 0.0,
    }


def _account(equity: str = "100000", cash: str = "1000") -> AlpacaAccount:
    return AlpacaAccount(equity=Decimal(equity), cash=Decimal(cash), buying_power=Decimal("10000"))


@pytest.mark.parametrize(
    "updates",
    [
        {"timestamp": datetime(2026, 1, 1)},
        {"equity": float("nan")},
        {"cash": float("inf")},
        {"return_since_start": float("inf")},
        {"n_positions": -1},
        {"benchmark_return_since_start": 0.1},
        {"alpha_since_start": 0.1},
        {"benchmark_return_since_start": 0.1, "alpha_since_start": float("nan")},
    ],
)
def test_account_equity_point_direct_and_unchecked_copy_reject_invalid_evidence(
    updates: dict,
) -> None:
    point = EquityPoint.model_validate(_payload())
    with pytest.raises(ValueError):
        EquityPoint.model_validate(dict(_payload(), **updates))
    with pytest.raises(ValueError):
        EquityPoint.model_validate(point.model_copy(update=updates))


@pytest.mark.parametrize("existing", [False, True])
@pytest.mark.parametrize("mutation", ["nan", "duplicate", "reverse"])
def test_account_equity_writer_rejects_invalid_batch_before_filesystem_changes(
    tmp_path: Path, existing: bool, mutation: str
) -> None:
    path = tmp_path / "ledger" / "curve.json"
    store = JsonFileEquityCurve(path)
    point = EquityPoint.model_validate(_payload())
    if existing:
        store.save([point])
    before = path.read_bytes() if existing else None
    second = point.model_copy(update={"timestamp": _NOW + timedelta(days=1)})
    if mutation == "nan":
        points = [point, second.model_copy(update={"cash": float("nan")})]
    elif mutation == "duplicate":
        points = [point, point]
    else:
        points = [second, point]
    with pytest.raises(ValueError):
        store.save(points)
    if existing:
        assert path.read_bytes() == before
    else:
        assert not path.parent.exists()


@pytest.mark.parametrize("baseline", [0.0, -1.0, float("nan"), float("inf")])
def test_account_equity_append_rejects_invalid_nominal_baseline(baseline: float) -> None:
    with pytest.raises(ValueError, match="starting_equity"):
        append_equity_point([], _account(), n_positions=1, now=_NOW, starting_equity=baseline)


@pytest.mark.parametrize("mutation", ["naive", "duplicate", "bad_history", "zero_inception"])
def test_account_equity_append_rejects_invalid_chronology_or_inception(mutation: str) -> None:
    point = EquityPoint.model_validate(_payload())
    now = _NOW + timedelta(days=1)
    if mutation == "naive":
        now = now.replace(tzinfo=None)
    elif mutation == "duplicate":
        now = _NOW
    elif mutation == "bad_history":
        point = point.model_copy(update={"cash": float("nan")})
    else:
        point = point.model_copy(update={"equity": 0.0, "return_since_start": -1.0})
    with pytest.raises(ValueError):
        append_equity_point([point], _account(), n_positions=1, now=now, benchmark_return=0.1)


def test_account_equity_offset_timestamp_normalizes_and_round_trips() -> None:
    point = EquityPoint.model_validate(
        dict(_payload(), timestamp=_NOW.astimezone(timezone(timedelta(hours=-7))))
    )
    assert point.timestamp.tzinfo is UTC
    assert EquityPoint.model_validate_json(point.model_dump_json()) == point


@pytest.mark.parametrize("equity", ["0", "-100"])
def test_account_equity_unmeasured_snapshot_preserves_insolvency_and_negative_cash(
    equity: str,
) -> None:
    point = append_equity_point([], _account(equity, "-1000"), n_positions=0, now=_NOW)[0]
    assert point.equity == float(equity)
    assert point.cash == -1000
    assert point.alpha_since_start is None


@given(
    baseline=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
    equity=st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False),
)
def test_account_equity_custom_nominal_return_preserves_analytic_ratio(
    baseline: float, equity: float
) -> None:
    point = append_equity_point(
        [], _account(str(equity)), n_positions=0, now=_NOW, starting_equity=baseline
    )[0]
    assert point.return_since_start == pytest.approx(equity / baseline - 1)


@pytest.mark.parametrize("count", [True, 0.5])
def test_account_equity_position_count_requires_integer_observation(count: object) -> None:
    with pytest.raises(ValueError):
        EquityPoint.model_validate(dict(_payload(), n_positions=count))


def test_account_equity_measured_snapshot_preserves_negative_current_balance() -> None:
    first = EquityPoint.model_validate(_payload())
    point = append_equity_point(
        [first],
        _account("-100", "-1000"),
        n_positions=0,
        now=_NOW + timedelta(days=1),
        benchmark_return=0.1,
    )[-1]
    assert point.equity == -100
    assert point.alpha_since_start == pytest.approx(-100 / 100000 - 1 - 0.1)


def test_account_equity_store_keeps_historical_alpha_formula_readable(tmp_path: Path) -> None:
    point = EquityPoint.model_validate(
        dict(
            _payload(),
            equity=95000.0,
            return_since_start=-0.05,
            benchmark_return_since_start=0.1,
            alpha_since_start=-0.15,
        )
    )
    path = tmp_path / "historical.json"
    store = JsonFileEquityCurve(path)
    store.save([point])
    assert store.all() == [point]


def test_account_equity_loader_rejects_duplicate_snapshot_history(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    point = EquityPoint.model_validate(_payload())
    path.write_text("[" + point.model_dump_json() + "," + point.model_dump_json() + "]")
    with pytest.raises(ValueError, match="strictly increasing"):
        JsonFileEquityCurve(path).all()
