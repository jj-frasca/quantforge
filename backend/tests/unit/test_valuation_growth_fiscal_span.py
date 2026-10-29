"""ADR-381: CAGR depends on labeled endpoints, not observation density."""

from collections.abc import Sequence

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from app.data.fundamentals import (
    AnnualFundamentals,
    FundamentalsHistory,
    parse_company_facts_history,
)
from app.research.valuation.intrinsic_value import (
    DcfAssumptions,
    dcf_intrinsic_value,
    estimate_growth,
)
from app.research.valuation.score import score_valuation


def _history(
    labels: Sequence[int], values: Sequence[float], leg: str = "free_cash_flow"
) -> FundamentalsHistory:
    rows = []
    for label, value in zip(labels, values, strict=True):
        fields = {"revenue": 500.0, "shares_diluted": 10.0, leg: value}
        rows.append(AnnualFundamentals(fiscal_year=label, **fields))
    return FundamentalsHistory(
        symbol="SYNTH",
        cik=1,
        entity_name="Synthetic fiscal span",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=tuple(rows),
    )


@pytest.mark.parametrize("leg", ["free_cash_flow", "net_income", "revenue"])
@pytest.mark.parametrize("labels", [(2020, 2024), (2019, 2020, 2024), (2019, 2021, 2024)])
def test_growth_annualizes_over_elapsed_labels(labels: tuple[int, ...], leg: str) -> None:
    values = [100.0, *([110.0] * (len(labels) - 2)), 120.0]
    history = _history(labels, values, leg)
    expected = 1.2 ** (1 / (labels[-1] - labels[0])) - 1
    assert estimate_growth(history) == pytest.approx(expected, rel=1e-13)


def test_canonical_parser_gap_uses_elapsed_years() -> None:
    def fact(year: int, value: float) -> dict[str, object]:
        return {
            "fy": year,
            "fp": "FY",
            "form": "10-K",
            "filed": f"{year + 1}-02-01",
            "accn": f"synthetic-{year}",
            "start": f"{year}-01-01",
            "end": f"{year}-12-31",
            "val": value,
        }

    history = parse_company_facts_history(
        {
            "cik": 1,
            "entityName": "Synthetic gap",
            "facts": {
                "us-gaap": {
                    "Revenues": {"units": {"USD": [fact(2020, 100.0), fact(2024, 120.0)]}},
                }
            },
        },
        "SYNTH",
    )
    assert [row.fiscal_year for row in history.years] == [2020, 2024]
    assert estimate_growth(history) == pytest.approx(1.2**0.25 - 1)


def test_dcf_matches_same_labeled_endpoints_with_intermediate_observations() -> None:
    sparse = _history([2020, 2024], [100.0, 120.0])
    dense = _history(range(2020, 2025), [100.0, 105.0, 110.0, 115.0, 120.0])
    expected = dcf_intrinsic_value(dense)
    assert expected.growth_rate_used == pytest.approx(1.2**0.25 - 1)
    assert expected.intrinsic_value_per_share == pytest.approx(179.70827136679333)
    assert dcf_intrinsic_value(sparse).model_dump() == expected.model_dump()


def test_valuation_uses_elapsed_growth_without_changing_composition() -> None:
    history = _history([2020, 2024], [100.0, 120.0])
    growth = 1.2**0.25 - 1
    fixed = DcfAssumptions(min_growth=growth, max_growth=growth)
    oracle = score_valuation(history, 100.0, assumptions=fixed)
    assert oracle.score == pytest.approx(0.4435425857728322)
    actual = score_valuation(history, 100.0)
    assert actual.dcf_assumptions == DcfAssumptions()
    assert oracle.dcf_assumptions == fixed
    assert actual.model_dump(exclude={"dcf_assumptions"}) == oracle.model_dump(
        exclude={"dcf_assumptions"}
    )


@pytest.mark.parametrize("leg", ["free_cash_flow", "net_income", "revenue"])
@pytest.mark.parametrize("labels", [(2020, 2020), (2024, 2020), (2020, 2024, 2022)])
def test_growth_refuses_duplicate_or_descending_labels_before_selection(
    labels: tuple[int, ...], leg: str
) -> None:
    with pytest.raises(ValueError, match="strictly increasing fiscal-year labels"):
        estimate_growth(_history(labels, [100.0 + i for i in range(len(labels))], leg))


@pytest.mark.parametrize("labels", [(2020, 2020), (2024, 2020), (2020, 2024, 2022)])
def test_invalid_labels_refuse_even_when_no_series_is_eligible(labels: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="strictly increasing fiscal-year labels"):
        estimate_growth(_history(labels, [-100.0] * len(labels), "revenue"))


@given(
    span=st.integers(min_value=2, max_value=30),
    base=st.integers(min_value=1, max_value=100_000),
    multiplier=st.integers(min_value=2, max_value=10),
    leg=st.sampled_from(["free_cash_flow", "net_income", "revenue"]),
)
@example(span=4, base=100, multiplier=2, leg="free_cash_flow")
def test_positive_observation_density_does_not_change_endpoint_cagr(
    span: int, base: int, multiplier: int, leg: str
) -> None:
    first, last = float(base), float(base * multiplier)
    dense = _history(
        range(2000, 2001 + span),
        [first + (last - first) * i / span for i in range(span + 1)],
        leg,
    )
    sparse = _history([2000, 2000 + span], [first, last], leg)
    assert estimate_growth(sparse) == estimate_growth(dense)


@pytest.mark.parametrize("leg", ["free_cash_flow", "net_income", "revenue"])
@pytest.mark.parametrize("values", [[100.0, 120.0], [100.0, 105.0, 120.0]])
def test_consecutive_labels_keep_exact_native_arithmetic(leg: str, values: list[float]) -> None:
    history = _history(range(2020, 2020 + len(values)), values, leg)
    assert estimate_growth(history) == (values[-1] / values[0]) ** (1 / (len(values) - 1)) - 1


@pytest.mark.parametrize("leg", ["free_cash_flow", "net_income", "revenue"])
def test_single_observed_year_keeps_unavailable_growth(leg: str) -> None:
    assert estimate_growth(_history([2020], [100.0], leg)) is None


def test_empty_growth_keeps_unavailable_result() -> None:
    assert estimate_growth(_history([], [])) is None


@pytest.mark.parametrize("values", [[-100.0, -120.0], [0.0, 120.0]])
def test_ineligible_observed_series_keeps_unavailable_result(values: list[float]) -> None:
    assert estimate_growth(_history([2020, 2024], values, "revenue")) is None


def test_dcf_early_nonpositive_base_return_does_not_claim_global_label_validation() -> None:
    history = _history([2024, 2020], [-100.0, -120.0])
    result = dcf_intrinsic_value(history)
    assert result.intrinsic_value_per_share is None
    assert result.flags == ["non-positive base cash flow — DCF not meaningful"]


@pytest.mark.parametrize(
    ("prior_fcf", "prior_income", "expected_ratio"),
    [(100.0, 100.0, 1.2), (None, 100.0, 1.8), (None, 0.0, 2.0)],
)
def test_gapped_growth_preserves_observed_series_precedence(
    prior_fcf: float | None, prior_income: float, expected_ratio: float
) -> None:
    history = FundamentalsHistory(
        symbol="SYNTH",
        cik=1,
        entity_name="Synthetic fiscal span",
        form="10-K",
        accession_number="synthetic",
        source_url="https://example.invalid/synthetic",
        years=(
            AnnualFundamentals(
                fiscal_year=2020,
                revenue=100.0,
                free_cash_flow=prior_fcf,
                net_income=prior_income,
            ),
            AnnualFundamentals(
                fiscal_year=2024, revenue=200.0, free_cash_flow=120.0, net_income=180.0
            ),
        ),
    )
    assert estimate_growth(history) == pytest.approx(expected_ratio**0.25 - 1)


def test_dcf_positive_inputs_propagate_label_order_refusal() -> None:
    with pytest.raises(ValueError, match="strictly increasing fiscal-year labels"):
        dcf_intrinsic_value(_history([2024, 2020], [100.0, 120.0]))


@pytest.mark.parametrize(("last", "expected"), [(80.0, 0.0), (100_000.0, 0.12)])
def test_gapped_growth_preserves_default_clamps(last: float, expected: float) -> None:
    result = dcf_intrinsic_value(_history([2020, 2024], [100.0, last]))
    assert result.growth_rate_used == expected
