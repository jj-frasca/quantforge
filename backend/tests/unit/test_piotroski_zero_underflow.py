"""ADR-395: definite nonzero quotient loss refuses before score booleans."""

import importlib
import math
from datetime import datetime
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import given
from hypothesis import strategies as st
from tests.unit.test_fundamentals_quality import _history
from tests.unit.test_piotroski_operand_validity import CONSUMERS, Consumer
from tests.unit.test_piotroski_ratio_validity import RATIOS

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.data.sources.edgar import SicClassification
from app.research.fundamentals.quality import piotroski_f_score


def _underflow_history(
    index: int, numerator: str, denominator: str, num_sign: float = 1.0, den_sign: float = 1.0
) -> FundamentalsHistory:
    rows = [
        AnnualFundamentals(fiscal_year=2024 + i, revenue=1.0, total_assets=1.0) for i in range(2)
    ]
    rows[index] = rows[index].model_copy(
        update={numerator: num_sign * 1e-308, denominator: den_sign * 1e308}
    )
    return _history(*rows)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("num_sign,den_sign", [(1.0, 1.0), (-1.0, 1.0), (1.0, -1.0), (-1.0, -1.0)])
def test_piotroski_all_signed_zero_underflows_refuse(
    consumer: Consumer,
    name: str,
    index: int,
    numerator: str,
    denominator: str,
    num_sign: float,
    den_sign: float,
) -> None:
    history = _underflow_history(index, numerator, denominator, num_sign, den_sign)
    row = history.years[index]
    a, b = getattr(row, numerator), getattr(row, denominator)
    assert a / b == 0.0 and Fraction(a) / Fraction(b) != 0
    assert math.copysign(1.0, a / b) == num_sign * den_sign
    with pytest.raises(
        ValueError, match=rf"{name} must not underflow to zero for Piotroski F-score"
    ):
        consumer(history)


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_piotroski_exact_positive_points_lost_to_zero_now_refuse(consumer: Consumer) -> None:
    history = _history(
        AnnualFundamentals(fiscal_year=2024, revenue=1.0, total_assets=1.0, net_income=0.0),
        AnnualFundamentals(
            fiscal_year=2025,
            revenue=1.0,
            total_assets=1e308,
            net_income=1e-308,
            operating_cash_flow=2e-308,
        ),
    )
    assert Fraction(2e-308) / Fraction(1e308) > Fraction(1e-308) / Fraction(1e308) > 0
    assert 2e-308 / 1e308 == 1e-308 / 1e308 == 0.0
    with pytest.raises(ValueError, match="roa_t must not underflow to zero"):
        consumer(history)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("error", ["raw", "later-nonfinite", "first-zero", "later-safety"])
def test_piotroski_zero_underflow_error_precedence(consumer: Consumer, error: str) -> None:
    history = _underflow_history(1, "net_income", "total_assets")
    latest = history.years[-1]
    if error == "raw":
        latest = latest.model_copy(update={"operating_cash_flow": math.inf})
        expected = r"latest\.operating_cash_flow must be finite"
    elif error == "later-nonfinite":
        latest = latest.model_copy(
            update={"total_current_assets": 1e308, "total_current_liabilities": 1e-308}
        )
        expected = "cr_t must be finite"
    else:
        latest = latest.model_copy(
            update={
                "operating_cash_flow": 2e-308,
                "retained_earnings": math.inf if error == "later-safety" else None,
            }
        )
        expected = "roa_t must not underflow to zero"
    with pytest.raises(ValueError, match=expected):
        consumer(_history(history.years[0], latest))


@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("zero", [0.0, -0.0])
def test_piotroski_true_signed_zero_numerators_stay_valid(
    name: str, index: int, numerator: str, denominator: str, zero: float
) -> None:
    history = _underflow_history(index, numerator, denominator)
    rows = list(history.years)
    rows[index] = rows[index].model_copy(update={numerator: zero})
    assert 0 <= piotroski_f_score(_history(*rows)).score <= 9


@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("denominator_value", [None, 0.0, -0.0])
def test_piotroski_unavailable_underflow_denominator_stays_unavailable(
    name: str, index: int, numerator: str, denominator: str, denominator_value: float | None
) -> None:
    history = _underflow_history(index, numerator, denominator)
    rows = list(history.years)
    rows[index] = rows[index].model_copy(update={denominator: denominator_value})
    assert 0 <= piotroski_f_score(_history(*rows)).score <= 9


@pytest.mark.parametrize("name,index,numerator,denominator", RATIOS)
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_piotroski_nonzero_subnormal_quotients_remain_native(
    name: str, index: int, numerator: str, denominator: str, sign: float
) -> None:
    history = _underflow_history(index, numerator, denominator)
    rows = list(history.years)
    rows[index] = rows[index].model_copy(update={numerator: sign * math.ulp(0.0), denominator: 1.0})
    assert getattr(rows[index], numerator) / getattr(rows[index], denominator) == sign * math.ulp(
        0.0
    )
    assert 0 <= piotroski_f_score(_history(*rows)).score <= 9


@pytest.mark.parametrize("name,index,numerator,denominator", [r for r in RATIOS if r[1] == 0])
def test_piotroski_inactive_prior_underflow_stays_ignored(
    name: str, index: int, numerator: str, denominator: str
) -> None:
    history = _underflow_history(index, numerator, denominator)
    prior = history.years[0].model_copy(update={"fiscal_year": 2022})
    assert 0 <= piotroski_f_score(_history(prior, history.years[1])).score <= 9


@pytest.mark.parametrize("name,index,numerator,denominator", [r for r in RATIOS if r[1] == 1])
def test_piotroski_latest_underflow_still_refuses_across_gap(
    name: str, index: int, numerator: str, denominator: str
) -> None:
    history = _underflow_history(index, numerator, denominator)
    prior = history.years[0].model_copy(update={"fiscal_year": 2022})
    with pytest.raises(ValueError, match=rf"{name} must not underflow to zero"):
        piotroski_f_score(_history(prior, history.years[1]))


@pytest.mark.parametrize("count", [0, 1])
def test_piotroski_short_history_underflow_retains_zero(count: int) -> None:
    row = _underflow_history(1, "net_income", "total_assets").years[-1]
    assert piotroski_f_score(_history(*([row] if count else []))).score == 0


@given(
    numerator=st.floats(
        min_value=math.ulp(0.0), max_value=1e-300, allow_nan=False, allow_infinity=False
    ),
    denominator=st.sampled_from([1e100, 1e200, 1e308]),
    sign=st.sampled_from([-1.0, 1.0]),
)
def test_piotroski_exact_nonzero_quotient_cannot_be_published_as_zero(
    numerator: float, denominator: float, sign: float
) -> None:
    assert sign * numerator / denominator == 0.0
    assert Fraction(sign * numerator) / Fraction(denominator) != 0
    history = _underflow_history(1, "net_income", "total_assets")
    latest = history.years[-1].model_copy(
        update={"net_income": sign * numerator, "total_assets": denominator}
    )
    with pytest.raises(ValueError, match="roa_t must not underflow to zero"):
        piotroski_f_score(_history(history.years[0], latest))


def test_piotroski_zero_underflow_aborts_real_mocked_sweep_before_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")
    events: list[str] = []
    bad = _underflow_history(1, "net_income", "total_assets")

    def fetch_history(symbol: str) -> FundamentalsHistory:
        events.append(f"fetch:{symbol}")
        return bad.model_copy(update={"symbol": symbol})

    def join_prices(
        adapter: object, symbol: str, history: FundamentalsHistory, now: datetime
    ) -> tuple[FundamentalsHistory, None]:
        events.append(f"prices:{symbol}")
        return history, None

    def classify(edgar: object, symbol: str) -> SicClassification:
        events.append(f"sic:{symbol}")
        return SicClassification(code=None, description=None)

    source = SimpleNamespace(all_tickers=lambda: ["BAD", "GOOD"], fetch_history=fetch_history)
    monkeypatch.setattr(sweep, "SecEdgarFundamentalsSource", lambda **kwargs: source)
    monkeypatch.setattr(sweep, "YFinanceAdapter", lambda **kwargs: object())
    monkeypatch.setattr(sweep, "_join_prices", join_prices)
    monkeypatch.setattr(sweep, "_sic_classification", classify)
    monkeypatch.setattr(sweep.time, "sleep", lambda seconds: None)
    output = tmp_path / "output"
    monkeypatch.setattr(sweep.sys, "argv", ["fundamental_sweep", "0", "1", str(output)])
    with pytest.raises(ValueError, match="roa_t must not underflow to zero"):
        sweep.main()
    assert events == ["fetch:BAD", "prices:BAD", "sic:BAD"]
    assert not output.exists()
