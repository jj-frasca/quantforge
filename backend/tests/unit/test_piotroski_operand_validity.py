"""ADR-389: raw invalid active F-score operands must not become boolean points."""

import importlib
import math
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from tests.unit.test_fundamentals_history import _facts
from tests.unit.test_fundamentals_quality import _history, _year

from app.data.fundamentals import (
    AnnualFundamentals,
    FundamentalsHistory,
    parse_company_facts_history,
)
from app.data.sources.edgar import SicClassification
from app.research.fundamentals.quality import FScore, QualityScore, piotroski_f_score, quality_score
from app.research.fundamentals.record import FundamentalRecord, compute_fundamental_record

Consumer = Callable[[FundamentalsHistory], FScore | QualityScore | FundamentalRecord]

LATEST = (
    "net_income",
    "total_assets",
    "operating_cash_flow",
    "long_term_debt",
    "total_current_assets",
    "total_current_liabilities",
    "gross_profit",
    "revenue",
    "shares_diluted",
)
PRIOR = tuple(field for field in LATEST if field != "operating_cash_flow")
ACTIVE = [("latest", field) for field in LATEST] + [("prior", field) for field in PRIOR]
CONSUMERS = [piotroski_f_score, quality_score, compute_fundamental_record]


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("role,field", ACTIVE)
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_piotroski_active_operands_refuse_before_boolean_erasure(
    consumer: Consumer, role: str, field: str, bad: float
) -> None:
    prior, latest = _year(2024), _year(2025)
    if role == "latest":
        latest = latest.model_copy(update={field: bad})
    else:
        prior = prior.model_copy(update={field: bad})
    with pytest.raises(ValueError, match=rf"{role}\.{field} must be finite for Piotroski F-score"):
        consumer(_history(prior, latest))


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("bad", [math.inf, "Infinity", math.nan, -math.inf])
def test_piotroski_actual_history_parser_invalid_cash_flow_refuses(
    consumer: Consumer, bad: float | str
) -> None:
    raw = _facts()
    raw["facts"]["us-gaap"]["NetCashProvidedByUsedInOperatingActivities"]["units"]["USD"][-1][
        "val"
    ] = bad
    history = parse_company_facts_history(raw, "SYN")
    with pytest.raises(ValueError, match=r"latest\.operating_cash_flow must be finite"):
        consumer(history)


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize(
    "role,field", [("latest", "operating_cash_flow"), ("prior", "long_term_debt")]
)
@pytest.mark.parametrize("peer", [None, 0.0])
def test_piotroski_missing_peer_or_zero_cannot_hide_active_invalidity(
    consumer: Consumer, role: str, field: str, peer: float | None
) -> None:
    prior, latest = _year(2024), _year(2025)
    if role == "latest":
        latest = latest.model_copy(update={field: math.inf, "total_assets": peer})
    else:
        prior = prior.model_copy(update={field: math.inf, "total_assets": peer})
    with pytest.raises(ValueError, match=rf"{role}\.{field} must be finite"):
        consumer(_history(prior, latest))


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_piotroski_first_active_error_precedes_later_safety_error(consumer: Consumer) -> None:
    history = _history(
        _year(2024, net_income=math.inf), _year(2025, net_income=math.nan, total_assets=math.inf)
    )
    with pytest.raises(ValueError, match=r"latest\.net_income must be finite for Piotroski"):
        consumer(history)


@pytest.mark.parametrize("count", [0, 1])
def test_piotroski_unavailable_short_history_keeps_existing_zero(count: int) -> None:
    history = _history(*([_year(2025, **dict.fromkeys(LATEST, math.inf))] if count else []))
    result = piotroski_f_score(history)
    assert result.score == 0
    assert not any(value for name, value in result.model_dump().items() if name != "score")


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_piotroski_gap_disables_prior_and_dilution_input_consumption(
    consumer: Consumer, bad: float
) -> None:
    prior, latest = _year(2023), _year(2025)
    expected = consumer(_history(prior, latest))
    prior = prior.model_copy(update=dict.fromkeys(LATEST, bad))
    latest = latest.model_copy(update={"shares_diluted": bad})
    assert consumer(_history(prior, latest)) == expected


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_piotroski_older_rows_and_prior_cash_flow_are_ignored(
    consumer: Consumer, bad: float
) -> None:
    prior, latest = _year(2024), _year(2025)
    expected = consumer(_history(prior, latest))
    prior = prior.model_copy(update={"operating_cash_flow": bad})
    older = _year(2020, **dict.fromkeys(LATEST, bad))
    assert consumer(_history(older, prior, latest)) == expected


@given(cash=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False))
@example(cash=math.ulp(0.0))
@example(cash=-math.ulp(0.0))
def test_piotroski_finite_cash_flow_retains_native_points(cash: float) -> None:
    history = _history(_year(2024), _year(2025, operating_cash_flow=cash))
    if cash != 0.0 and cash / 2000.0 == 0.0:
        with pytest.raises(ValueError, match="cfo_over_assets_t must not underflow to zero"):
            piotroski_f_score(history)
        return
    f = piotroski_f_score(history)
    assert f.cfo_positive is (cash > 0.0)
    assert f.accruals_quality is (cash / 2000.0 > 100.0 / 2000.0)
    assert f.score == sum(value for key, value in f.model_dump().items() if key != "score")


@pytest.mark.parametrize("consumer", CONSUMERS)
def test_piotroski_finite_operand_overflow_reaches_derived_ratio_guard(
    consumer: Consumer,
) -> None:
    prior = AnnualFundamentals(fiscal_year=2024, revenue=1.0, net_income=0.0, total_assets=1.0)
    latest = AnnualFundamentals(
        fiscal_year=2025,
        revenue=1.0,
        net_income=0.0,
        total_assets=1e-308,
        operating_cash_flow=1e308,
    )
    with pytest.raises(ValueError, match="cfo_over_assets_t must be finite for Piotroski F-score"):
        consumer(_history(prior, latest))


@pytest.mark.parametrize("derived_overflow", [False, True])
def test_piotroski_actual_sweep_refuses_before_output_or_next_company(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, derived_overflow: bool
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")
    events: list[str] = []
    bad = _history(_year(2024), _year(2025, operating_cash_flow=math.inf))
    error = r"latest\.operating_cash_flow must be finite"
    if derived_overflow:
        bad = _history(
            AnnualFundamentals(fiscal_year=2024, revenue=1.0, total_assets=1.0),
            AnnualFundamentals(
                fiscal_year=2025, revenue=1.0, total_assets=1e-308, operating_cash_flow=1e308
            ),
        )
        error = "cfo_over_assets_t must be finite"

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
    with pytest.raises(ValueError, match=error):
        sweep.main()
    assert events == ["fetch:BAD", "prices:BAD", "sic:BAD"]
    assert not output.exists()
