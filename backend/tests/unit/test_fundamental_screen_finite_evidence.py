"""ADR-378: enabled fundamental checks veto nonfinite numeric evidence."""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.data.fundamentals import (
    FundamentalCriteria,
    FundamentalSnapshot,
    parse_company_facts,
    screen_fundamentals,
)

FIELDS = (
    ("revenue_growth_yoy", "min_revenue_growth_yoy", "revenue growth"),
    ("net_margin", "min_net_margin", "net margin"),
)
NONFINITE = (float("nan"), float("inf"), -float("inf"))


def _snapshot(field: str, metric: float | None) -> FundamentalSnapshot:
    return FundamentalSnapshot.model_validate(
        {
            "symbol": "SYNTH",
            "cik": 1,
            "entity_name": "Synthetic",
            "fiscal_year": 2024,
            "form": "10-K",
            "accession_number": "synthetic",
            "source_url": "https://example.invalid",
            "revenue": 100.0,
            "revenue_growth_yoy": 0.1,
            "net_margin": 0.1,
            field: metric,
        }
    )


@pytest.mark.parametrize(("field", "criterion", "label"), FIELDS)
@pytest.mark.parametrize("metric", NONFINITE)
def test_enabled_fundamental_check_vetoes_nonfinite_metric(
    field: str, criterion: str, label: str, metric: float
) -> None:
    config = FundamentalCriteria.model_validate(
        {"min_revenue_growth_yoy": None, "min_net_margin": None, criterion: 0.0}
    )
    screen = screen_fundamentals(_snapshot(field, metric), config)
    assert screen.passed is False
    assert screen.reasons == [f"{label} is not finite (cannot verify)"]


@pytest.mark.parametrize(("field", "criterion", "label"), FIELDS)
@pytest.mark.parametrize("metric", NONFINITE)
def test_disabled_fundamental_check_ignores_nonfinite_metric(
    field: str, criterion: str, label: str, metric: float
) -> None:
    config = FundamentalCriteria.model_validate({criterion: None})
    screen = screen_fundamentals(_snapshot(field, metric), config)
    assert screen.passed is True
    assert screen.reasons == []


@pytest.mark.parametrize(("field", "criterion", "label"), FIELDS)
def test_missing_fundamental_metric_keeps_existing_reason(
    field: str, criterion: str, label: str
) -> None:
    screen = screen_fundamentals(_snapshot(field, None), FundamentalCriteria())
    assert screen.passed is False
    assert screen.reasons == [f"{label} unavailable (cannot verify)"]


@pytest.mark.parametrize(("field", "criterion", "label"), FIELDS)
@settings(max_examples=50, deadline=None)
@given(
    threshold=st.floats(allow_nan=False, allow_infinity=False), metric=st.sampled_from(NONFINITE)
)
def test_no_finite_enabled_minimum_admits_nonfinite_metric(
    field: str, criterion: str, label: str, threshold: float, metric: float
) -> None:
    config = FundamentalCriteria.model_validate(
        {"min_revenue_growth_yoy": None, "min_net_margin": None, criterion: threshold}
    )
    assert screen_fundamentals(_snapshot(field, metric), config).passed is False


@pytest.mark.parametrize("current", [1e308, -1e308])
def test_finite_company_facts_overflow_cannot_satisfy_enabled_growth_check(current: float) -> None:
    def fact(value: float, year: int) -> dict[str, object]:
        assert math.isfinite(value)
        return {
            "val": value,
            "fy": year,
            "fp": "FY",
            "form": "10-K",
            "accn": "synthetic",
            "filed": f"{year + 1}-02-01",
        }

    gaap = {
        "Revenues": {"units": {"USD": [fact(1e-308, 2023), fact(current, 2024)]}},
        "NetIncomeLoss": {"units": {"USD": [fact(current, 2024)]}},
    }
    snapshot = parse_company_facts(
        {"cik": 1, "entityName": "Synthetic", "facts": {"us-gaap": gaap}}, "SYNTH"
    )
    assert snapshot.revenue_growth_yoy is not None
    assert math.isinf(snapshot.revenue_growth_yoy)
    assert snapshot.net_margin == 1.0
    screen = screen_fundamentals(snapshot, FundamentalCriteria())
    assert screen.passed is False
    assert screen.reasons == ["revenue growth is not finite (cannot verify)"]


@pytest.mark.parametrize("growth", NONFINITE)
@pytest.mark.parametrize("margin", NONFINITE)
@pytest.mark.parametrize("enabled", [False, True])
def test_two_nonfinite_metrics_respect_explicit_check_enablement(
    growth: float, margin: float, enabled: bool
) -> None:
    snapshot = _snapshot("revenue_growth_yoy", growth).model_copy(update={"net_margin": margin})
    config = FundamentalCriteria(
        min_revenue_growth_yoy=0.0 if enabled else None,
        min_net_margin=0.0 if enabled else None,
    )
    screen = screen_fundamentals(snapshot, config)
    assert screen.passed is (not enabled)
    assert screen.reasons == (
        ["revenue growth is not finite (cannot verify)", "net margin is not finite (cannot verify)"]
        if enabled
        else []
    )
