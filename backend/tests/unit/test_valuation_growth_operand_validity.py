"""ADR-406: each attempted growth series carries finite raw evidence."""

import math
from collections.abc import Callable, Sequence

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.data.fundamentals import AnnualFundamentals, FundamentalsHistory
from app.research.fundamentals.record import compute_fundamental_record
from app.research.valuation.intrinsic_value import dcf_intrinsic_value, estimate_growth
from app.research.valuation.score import score_valuation


def _history(field: str, values: Sequence[float | None]) -> FundamentalsHistory:
    rows = []
    for i, value in enumerate(values):
        data: dict[str, float | None] = {
            "free_cash_flow": 100.0,
            "net_income": 1.0,
            "revenue": 100.0,
            "shares_diluted": 10.0,
            "gross_profit": 25.0,
            "total_assets": 100.0,
        }
        if field != "free_cash_flow":
            data["free_cash_flow"] = None
        if field == "revenue":
            data["net_income"] = 120.0 if i == len(values) - 1 else None
        data[field] = value
        rows.append(AnnualFundamentals(fiscal_year=2023 + i, **data))
    return FundamentalsHistory(
        symbol="TEST",
        cik=1,
        entity_name="Synthetic",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=tuple(rows),
    )


@pytest.mark.parametrize("consume", [estimate_growth, dcf_intrinsic_value])
@pytest.mark.parametrize("field", ["free_cash_flow", "net_income", "revenue"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_growth_refuses_attempted_nonfinite_observations(
    consume: Callable[[FundamentalsHistory], object],
    field: str,
    invalid: float,
    position: int,
) -> None:
    values = [100.0, 110.0, 120.0]
    values[position] = invalid
    # ADR-408: selected latest base refuses before DCF reaches growth estimation.
    # Still exercise the direct estimator's own raw-series contract separately.
    if field in ("free_cash_flow", "net_income") and position == 2:
        with pytest.raises(
            ValueError,
            match=rf"^{field} for fiscal year 2025 must be finite for DCF base$",
        ):
            dcf_intrinsic_value(_history(field, values))
        consume = estimate_growth
    with pytest.raises(
        ValueError,
        match=rf"^{field} for fiscal year {2023 + position} must be finite for valuation growth$",
    ):
        consume(_history(field, values))


@pytest.mark.parametrize("consume", [score_valuation, compute_fundamental_record])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("position", [0, 1, 2])
def test_growth_refusal_reaches_finite_valuation_record_consumers(
    consume: Callable[..., object],
    invalid: float,
    position: int,
) -> None:
    values = [100.0, 110.0, 120.0]
    values[position] = invalid
    # ADR-408 intentionally gives the selected latest base earlier precedence.
    context = "DCF base" if position == 2 else "valuation growth"
    with pytest.raises(
        ValueError,
        match=rf"^free_cash_flow for fiscal year {2023 + position} must be finite for {context}$",
    ):
        consume(_history("free_cash_flow", values), 100.0)


@pytest.mark.parametrize("field", ["free_cash_flow", "net_income", "revenue"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
@pytest.mark.parametrize("peer", [0.0, -1.0])
def test_growth_nonpositive_peers_do_not_hide_invalid_series(
    field: str,
    invalid: float,
    peer: float,
) -> None:
    with pytest.raises(
        ValueError, match=rf"^{field} for fiscal year 2024 must be finite for valuation growth$"
    ):
        estimate_growth(_history(field, [peer, invalid, 120.0]))


@pytest.mark.parametrize("field", ["free_cash_flow", "net_income"])
@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_growth_missing_peer_does_not_hide_invalid_series(field: str, invalid: float) -> None:
    with pytest.raises(
        ValueError, match=rf"^{field} for fiscal year 2024 must be finite for valuation growth$"
    ):
        estimate_growth(_history(field, [None, invalid, 120.0]))


def test_growth_first_invalid_field_and_year_are_deterministic() -> None:
    source = _history("free_cash_flow", [math.inf, math.nan, 120.0])
    with pytest.raises(
        ValueError,
        match=r"^free_cash_flow for fiscal year 2023 must be finite for valuation growth$",
    ):
        estimate_growth(source)


@pytest.mark.parametrize("consume", [estimate_growth, dcf_intrinsic_value])
def test_growth_ignores_invalid_lower_priority_series(
    consume: Callable[[FundamentalsHistory], object],
) -> None:
    source = _history("free_cash_flow", [100.0, 110.0, 120.0])
    bad = source.model_copy(
        update={
            "years": tuple(
                y.model_copy(update={"net_income": math.inf, "revenue": math.nan})
                for y in source.years
            )
        }
    )
    assert consume(bad) == consume(source)


@pytest.mark.parametrize("values", [[], [math.nan]])
def test_growth_short_history_remains_unmeasured(values: list[float]) -> None:
    assert estimate_growth(_history("free_cash_flow", values)) is None


def test_growth_chronology_still_precedes_series_validity() -> None:
    source = _history("free_cash_flow", [math.inf, 120.0])
    bad = source.model_copy(update={"years": source.years[::-1]})
    with pytest.raises(ValueError, match="strictly increasing fiscal-year labels"):
        estimate_growth(bad)


@pytest.mark.parametrize("early", ["base", "shares"])
def test_dcf_early_returns_still_bypass_growth_input_consumption(early: str) -> None:
    source = _history("free_cash_flow", [math.inf, 120.0])
    latest = source.years[-1].model_copy(
        update={"free_cash_flow": 0.0} if early == "base" else {"shares_diluted": None}
    )
    source = source.model_copy(update={"years": (source.years[0], latest)})
    assert dcf_intrinsic_value(source).intrinsic_value_per_share is None


def test_growth_finite_arithmetic_overflow_remains_separate() -> None:
    assert estimate_growth(_history("free_cash_flow", [1e-308, 1e308])) == math.inf


@given(
    fcf=st.lists(
        st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
        min_size=3,
        max_size=3,
    ),
    income=st.lists(
        st.one_of(st.none(), st.floats(allow_nan=False, allow_infinity=False)),
        min_size=3,
        max_size=3,
    ),
    revenue=st.lists(st.floats(allow_nan=False, allow_infinity=False), min_size=3, max_size=3),
)
def test_growth_finite_missing_series_preserve_native_selection(
    fcf: list[float | None],
    income: list[float | None],
    revenue: list[float],
) -> None:
    source = _history("free_cash_flow", fcf)
    source = source.model_copy(
        update={
            "years": tuple(
                y.model_copy(update={"net_income": income[i], "revenue": revenue[i]})
                for i, y in enumerate(source.years)
            )
        }
    )
    expected = None
    for series in (fcf, income, revenue):
        if any(v is None or v <= 0 for v in series):
            continue
        first, last = series[0], series[-1]
        assert first is not None and last is not None
        expected = (last / first) ** (1 / 2) - 1
        break
    actual = estimate_growth(source)
    if expected is None:
        assert actual is None
    else:
        assert actual is not None and actual.hex() == expected.hex()
