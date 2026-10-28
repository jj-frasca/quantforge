"""ADR-397: exact accepted-operand predicates refuse native comparison loss."""

import importlib
import math
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from hypothesis import example, given
from hypothesis import strategies as st
from tests.unit.test_fundamentals_quality import _history
from tests.unit.test_piotroski_operand_validity import CONSUMERS, Consumer

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.data.sources.edgar import SicClassification
from app.research.fundamentals.quality import piotroski_f_score

PAIRS = [
    ("delta_roa_positive", "net_income", "total_assets", "net_income", "total_assets", False),
    (
        "accruals_quality",
        "operating_cash_flow",
        "total_assets",
        "net_income",
        "total_assets",
        False,
    ),
    (
        "delta_leverage_negative",
        "long_term_debt",
        "total_assets",
        "long_term_debt",
        "total_assets",
        True,
    ),
    (
        "delta_current_ratio_positive",
        "total_current_assets",
        "total_current_liabilities",
        "total_current_assets",
        "total_current_liabilities",
        False,
    ),
    ("delta_gross_margin_positive", "gross_profit", "revenue", "gross_profit", "revenue", False),
    ("delta_asset_turnover_positive", "revenue", "total_assets", "revenue", "total_assets", False),
]


def _pair_history(
    pair: tuple[str, str, str, str, str, bool],
    regime: str = "ordinary",
    sign: float = 1.0,
    direction: str = "lost-true",
) -> FundamentalsHistory:
    name, an, ad, bn, bd, less = pair
    a, d = (7.0, 3.0) if regime == "ordinary" else (1.0, 1.7e308)
    b = math.nextafter(a, math.inf)
    if direction == "strict":
        b = 2 * a
    left, right = (a, b) if less else (b, a)
    if direction == "false":
        left, right = right, left
    elif direction == "equal":
        left = right
    prior = {"fiscal_year": 2024, "revenue": 1.0, "total_assets": 1.0}
    latest = {"fiscal_year": 2025, "revenue": 1.0, "total_assets": 1.0}
    latest.update({an: sign * left, ad: sign * d})
    other = latest if name == "accruals_quality" else prior
    other.update({bn: sign * right, bd: sign * d})
    return _history(AnnualFundamentals(**prior), AnnualFundamentals(**latest))


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("pair", PAIRS, ids=[p[0] for p in PAIRS])
@pytest.mark.parametrize("regime", ["ordinary", "subnormal"])
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_all_six_lost_true_predicates_refuse(
    consumer: Consumer, pair: tuple, regime: str, sign: float
) -> None:
    h = _pair_history(pair, regime, sign)
    name, an, ad, bn, bd, less = pair
    t, p = h.years[-1], h.years[-1] if name == "accruals_quality" else h.years[0]
    a, b, c, d = getattr(t, an), getattr(t, ad), getattr(p, bn), getattr(p, bd)
    x, y = Fraction(a) / Fraction(b), Fraction(c) / Fraction(d)
    assert a / b == c / d != 0
    assert x < y if less else x > y
    with pytest.raises(
        ValueError, match=rf"{name} must preserve exact operand ordering for Piotroski F-score"
    ):
        consumer(h)


@pytest.mark.parametrize("pair", PAIRS, ids=[p[0] for p in PAIRS])
@pytest.mark.parametrize("regime", ["ordinary", "subnormal"])
@pytest.mark.parametrize("sign", [1.0, -1.0])
@pytest.mark.parametrize("direction", ["false", "equal", "strict"])
def test_native_agreement_does_not_refuse_unequal_quotients(
    pair: tuple, regime: str, sign: float, direction: str
) -> None:
    f = piotroski_f_score(_pair_history(pair, regime, sign, direction))
    assert getattr(f, pair[0]) is (direction == "strict")
    assert f.score == sum(v for k, v in f.model_dump().items() if k != "score")


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("pair", PAIRS, ids=[p[0] for p in PAIRS])
@pytest.mark.parametrize("field", ["numerator", "denominator", "zero"])
def test_unavailable_pair_preserves_false(consumer: Consumer, pair: tuple, field: str) -> None:
    h = _pair_history(pair)
    target = pair[1] if field == "numerator" else pair[2]
    t = h.years[-1].model_copy(update={target: 0.0 if field == "zero" else None})
    f = consumer(_history(h.years[0], t))
    if field != "zero" or target == pair[2]:
        observed = f if hasattr(f, pair[0]) else f.f_score
        if isinstance(observed, int):
            reference = piotroski_f_score(_history(h.years[0], t))
            assert not getattr(reference, pair[0])
            assert observed == reference.score
        else:
            assert not getattr(observed, pair[0])


@pytest.mark.parametrize("pair", PAIRS, ids=[p[0] for p in PAIRS])
def test_fiscal_gap_disables_only_prior_pair(pair: tuple) -> None:
    h = _pair_history(pair)
    h = _history(h.years[0].model_copy(update={"fiscal_year": 2022}), h.years[-1])
    if pair[0] == "accruals_quality":
        with pytest.raises(ValueError, match="accruals_quality must preserve"):
            piotroski_f_score(h)
    else:
        assert not getattr(piotroski_f_score(h), pair[0])


@pytest.mark.parametrize("count", [0, 1])
def test_short_history_precision_is_inactive(count: int) -> None:
    h = _pair_history(PAIRS[1])
    assert piotroski_f_score(_history(*h.years[-count:] if count else ())).score == 0


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("earlier", ["raw", "nonfinite", "zero", "first-pair", "safety"])
def test_precision_error_precedence(consumer: Consumer, earlier: str) -> None:
    h = _pair_history(PAIRS[1])
    t = h.years[-1]
    if earlier == "raw":
        t = t.model_copy(update={"gross_profit": math.inf})
        expected = r"latest\.gross_profit must be finite"
    elif earlier == "nonfinite":
        t = t.model_copy(update={"gross_profit": 1e308, "revenue": 1e-308})
        expected = "gm_t must be finite"
    elif earlier == "zero":
        t = t.model_copy(update={"gross_profit": 1e-308, "revenue": 1e308})
        expected = "gm_t must not underflow to zero"
    elif earlier == "first-pair":
        h = _pair_history(PAIRS[0])
        t = h.years[-1].model_copy(update={"operating_cash_flow": math.nextafter(7.0, math.inf)})
        expected = "delta_roa_positive must preserve"
    else:
        t = t.model_copy(update={"retained_earnings": math.inf})
        expected = "accruals_quality must preserve"
    with pytest.raises(ValueError, match=expected):
        consumer(_history(h.years[0], t))


@pytest.mark.parametrize("kind", ["int", "npint", "npuint"])
def test_original_integral_operands_normalize_without_float_projection(kind: str) -> None:
    cash = {"int": 2**64 - 1, "npint": np.int64(2**63 - 1), "npuint": np.uint64(2**64 - 1)}[kind]
    income = float(2**63 if kind == "npint" else 2**64)
    h = _pair_history(PAIRS[1])
    t = h.years[-1].model_copy(
        update={"net_income": income, "operating_cash_flow": cash, "total_assets": -3.0}
    )
    assert Fraction(int(cash)) / -3 > Fraction(income) / -3
    with pytest.raises(ValueError, match="accruals_quality must preserve"):
        piotroski_f_score(_history(h.years[0], t))


@pytest.mark.parametrize(
    "kind", ["fraction", "decimal", "float16", "float32", "float64", "longdouble"]
)
def test_native_exact_scalar_protocol_retains_agreement_without_projection(kind: str) -> None:
    typ = {
        "fraction": Fraction,
        "decimal": Decimal,
        "float16": np.float16,
        "float32": np.float32,
        "float64": np.float64,
        "longdouble": np.longdouble,
    }[kind]
    income, assets = typ(7), typ(3)
    cash = (
        typ("7.000000000000000001")
        if kind in ("fraction", "decimal", "longdouble")
        else income + typ(1)
    )
    if cash == income:  # platforms whose longdouble is binary64 still exercise valid agreement
        cash = income + typ(1)
    if kind == "longdouble" and np.finfo(np.longdouble).nmant > 52:
        assert float(cash) == float(income) and cash != income
    h = _pair_history(PAIRS[1])
    t = h.years[-1].model_copy(
        update={
            "net_income": income,
            "operating_cash_flow": cash,
            "total_assets": assets,
            "revenue": typ(1),
        }
    )
    assert piotroski_f_score(_history(h.years[0], t)).accruals_quality


@pytest.mark.parametrize("kind", [Fraction, Decimal, np.longdouble])
def test_validated_schema_precision_is_accepted_float_not_original_decimal(kind: type) -> None:
    original = kind("7.00000000000000000001")
    t = AnnualFundamentals(
        fiscal_year=2025, revenue=1, total_assets=3, net_income=7, operating_cash_flow=original
    )
    assert type(t.operating_cash_flow) is float and t.operating_cash_flow == 7.0
    assert not piotroski_f_score(
        _history(AnnualFundamentals(fiscal_year=2024, revenue=1), t)
    ).accruals_quality


@pytest.mark.parametrize(
    "pair",
    [None, (1,), (1, 2, 3), [1, 2], (1.0, 2), (1, 2.0), (True, 2), (1, False), (1, 0), ("1", 2)],
)
def test_malformed_exact_protocol_refuses_only_active_pair(pair: object) -> None:
    class Scalar(float):
        def as_integer_ratio(self) -> object:
            return pair

    h = _pair_history(PAIRS[1], direction="strict")
    t = h.years[-1].model_copy(update={"operating_cash_flow": Scalar(14)})
    with pytest.raises(ValueError, match="accruals_quality requires exact operand ratios"):
        piotroski_f_score(_history(h.years[0], t))
    # Same unsupported scalar is inactive when its partner ratio is absent.
    t = t.model_copy(update={"net_income": None})
    assert not piotroski_f_score(_history(h.years[0], t)).accruals_quality


@given(
    income=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    cash=st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    assets=st.sampled_from([-3.0, 3.0, 1e6]),
)
@example(income=7.0, cash=math.nextafter(7.0, math.inf), assets=3.0)
def test_accrual_predicate_cannot_disagree_with_exact_accepted_operands(
    income: float, cash: float, assets: float
) -> None:
    h = _history(
        AnnualFundamentals(fiscal_year=2024, revenue=0.0),
        AnnualFundamentals(
            fiscal_year=2025,
            revenue=0,
            total_assets=assets,
            net_income=income,
            operating_cash_flow=cash,
        ),
    )
    if (income != 0 and income / assets == 0) or (cash != 0 and cash / assets == 0):
        with pytest.raises(ValueError, match="must not underflow to zero"):
            piotroski_f_score(h)
    elif (cash / assets > income / assets) != (
        Fraction(cash) / Fraction(assets) > Fraction(income) / Fraction(assets)
    ):
        with pytest.raises(ValueError, match="accruals_quality must preserve"):
            piotroski_f_score(h)
    else:
        assert piotroski_f_score(h).accruals_quality is (cash / assets > income / assets)


def test_precision_refusal_aborts_real_mocked_sweep_before_output(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    sweep = importlib.import_module("scripts.fundamental_sweep")
    events: list[str] = []
    bad = _pair_history(PAIRS[1])

    def fetch_history(symbol: str) -> FundamentalsHistory:
        events.append(f"fetch:{symbol}")
        return bad.model_copy(update={"symbol": symbol})

    def join_prices(
        adapter: object, symbol: str, history: FundamentalsHistory, now: datetime
    ) -> tuple:
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
    with pytest.raises(ValueError, match="accruals_quality must preserve"):
        sweep.main()
    assert events == ["fetch:BAD", "prices:BAD", "sic:BAD"]
    assert not output.exists()


@pytest.mark.parametrize("consumer", CONSUMERS)
@pytest.mark.parametrize("pair", PAIRS, ids=[p[0] for p in PAIRS])
def test_native_true_exact_false_also_refuses(consumer: Consumer, pair: tuple) -> None:
    h = _pair_history(pair)
    name, an, ad, bn, bd, less = pair
    rows = list(h.years)
    rows[1] = rows[1].model_copy(
        update={an: 1.0 if less else Fraction(1), ad: 3.0 if less else Fraction(3)}
    )
    index = 1 if name == "accruals_quality" else 0
    right_denom = Fraction(3) if less or index == 1 else 3.0
    rows[index] = rows[index].model_copy(update={bn: Fraction(1) if less else 1.0, bd: right_denom})
    t, p = rows[1], rows[index]
    left, right = getattr(t, an) / getattr(t, ad), getattr(p, bn) / getattr(p, bd)
    assert left < right if less else left > right
    assert Fraction(getattr(t, an)) / Fraction(getattr(t, ad)) == Fraction(
        getattr(p, bn)
    ) / Fraction(getattr(p, bd))
    with pytest.raises(ValueError, match=rf"{name} must preserve exact operand ordering"):
        consumer(_history(*rows))


@pytest.mark.parametrize("error", [AttributeError, TypeError, ValueError, OverflowError])
def test_unavailable_exact_protocol_has_named_refusal(error: type[Exception]) -> None:
    class Scalar(float):
        def as_integer_ratio(self) -> tuple[int, int]:
            raise error("unavailable precision")

    h = _pair_history(PAIRS[1], direction="strict")
    t = h.years[-1].model_copy(update={"operating_cash_flow": Scalar(14)})
    with pytest.raises(ValueError, match="accruals_quality requires exact operand ratios"):
        piotroski_f_score(_history(h.years[0], t))
