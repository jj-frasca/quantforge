"""Explicit annual periods and observed-source eligibility (ADR-421); no network."""

import gzip
import hashlib
import importlib
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given
from hypothesis import strategies as st

OBSERVED = datetime(2026, 11, 7, tzinfo=UTC)
ACCESSION = "0000320193-19-000119"
START, END = "2018-09-30", "2019-09-28"


def api() -> ModuleType:
    return importlib.import_module("app.data.anchored_fundamentals")


def anchor(**changes: object) -> object:
    values: dict[str, object] = {
        "cik": 320193,
        "fiscal_year": 2019,
        "accession_number": ACCESSION,
        "annual_start": date.fromisoformat(START),
        "report_end": date.fromisoformat(END),
        "original": api().SourceObservation(url="original", sha256="a" * 64, observed_at=OBSERVED),
        "header_labels": {"acceptance": "20191030181236", "filed": "20191031"},
    }
    values.update(changes)
    return api().FilingAnnualAnchor(**values)


def row(value: object, *, instant: bool = False, **changes: object) -> dict[str, object]:
    result: dict[str, object] = {
        "val": value,
        "accn": ACCESSION,
        "form": "10-K",
        "fy": 2030,
        "fp": "Q1",
        "end": END,
    }
    if not instant:
        result["start"] = START
    result.update(changes)
    return result


def base() -> dict:
    return {
        "cik": 320193,
        "entityName": "Issuer",
        "facts": {
            "us-gaap": {"Revenues": {"units": {"USD": [row(100), row(25, start="2019-06-30")]}}}
        },
    }


def put(data: dict, tag: str, rows: list[dict[str, object]], unit: str = "USD") -> None:
    data["facts"]["us-gaap"][tag] = {"units": {unit: rows}}


def evaluate(data: dict, **changes: object) -> object:
    raw = json.dumps(data).encode()
    args: dict[str, object] = {
        "raw": raw,
        "symbol": "TEST",
        "anchor": anchor(),
        "as_of": OBSERVED,
        "observation": api().SourceObservation(
            url="companyfacts",
            sha256=hashlib.sha256(raw).hexdigest(),
            observed_at=OBSERVED - timedelta(days=1),
        ),
    }
    args.update(changes)
    return api().evaluate_anchored_fundamentals(**args)


def test_anchored_flows_instants_and_existing_score_retain_wrapper() -> None:
    data = base()
    put(data, "NetIncomeLoss", [row(10), row(3, start="2019-06-30")])
    put(data, "Assets", [row(200, instant=True), row(900, instant=True, end="2018-09-29")])
    put(
        data,
        "WeightedAverageNumberOfDilutedSharesOutstanding",
        [row(20), row(99, instant=True)],
        "shares",
    )
    result = evaluate(data)
    year = result.history.years[0]
    assert (year.fiscal_year, year.period_end, year.revenue, year.net_income) == (
        2019,
        date(2019, 9, 28),
        100,
        10,
    )
    assert (year.total_assets, year.shares_diluted) == (200, 20)
    assert result.available_at == OBSERVED
    assert result.record.value_score is result.record.combined_score is None
    assert result.record.f_score == 0  # unchanged insufficient-history behavior
    assert result.record.history_citation.accession_number == ACCESSION
    assert result.anchor.header_labels["acceptance"] == "20191030181236"
    assert "eps" in result.missing_fields and "revenue" not in result.missing_fields
    assert year.flow_facts.revenue.row["fy"] == 2030  # actual supplied label retained
    assert result.model_dump_json()


@pytest.mark.parametrize(
    "changes",
    [{"start": "2019-06-30"}, {"end": "2019-09-27"}, {"accn": "other"}, {"form": "10-K/A"}],
)
def test_anchored_revenue_requires_exact_identity(changes: dict[str, object]) -> None:
    data = base()
    put(data, "Revenues", [row(100, **changes)])
    with pytest.raises(ValueError, match="revenue"):
        evaluate(data)


def test_anchored_fallback_uses_only_eligible_tags() -> None:
    data = base()
    put(data, "RevenueFromContractWithCustomerExcludingAssessedTax", [row(999, start="2019-06-30")])
    assert evaluate(data).history.years[0].revenue == 100


@pytest.mark.parametrize("value", [101, True, None, "100", float("inf"), float("nan"), 2**53 + 1])
def test_anchored_conflicting_or_malformed_revenue_refuses(value: object) -> None:
    data = base()
    put(data, "RevenueFromContractWithCustomerExcludingAssessedTax", [row(100), row(value)])
    with pytest.raises(ValueError):
        evaluate(data)


def test_anchored_conflict_precedes_binary64_projection() -> None:
    data = base()
    put(data, "Revenues", [row(2**53), row(2**53 + 1)])
    with pytest.raises(ValueError, match="conflicting"):
        evaluate(data)


def test_anchored_null_start_is_not_an_instant() -> None:
    data = base()
    put(data, "Assets", [row(999, instant=True, start=None)])
    result = evaluate(data)
    assert result.history.years[0].total_assets is None
    assert "total_assets" in result.missing_fields


@pytest.mark.parametrize(
    "as_of",
    [
        datetime(2019, 10, 31, tzinfo=UTC),
        OBSERVED - timedelta(microseconds=1),
        datetime(2027, 1, 1),
    ],
)
def test_anchored_refuses_unavailable_or_naive_cutoff(as_of: datetime) -> None:
    with pytest.raises(ValueError, match=r"observ|aware"):
        evaluate(base(), as_of=as_of)


def test_anchored_checks_company_capture_time_too() -> None:
    data = base()
    raw = json.dumps(data).encode()
    later = OBSERVED + timedelta(days=1)
    observation = api().SourceObservation(
        url="source", sha256=hashlib.sha256(raw).hexdigest(), observed_at=later
    )
    with pytest.raises(ValueError, match="observ"):
        evaluate(data, observation=observation)
    assert evaluate(data, observation=observation, as_of=later).available_at == later


@pytest.mark.parametrize("change", ["sha", "cik"])
def test_anchored_refuses_source_identity_mismatch(change: str) -> None:
    data = base()
    args = {}
    if change == "sha":
        args["observation"] = api().SourceObservation(
            url="source", sha256="0" * 64, observed_at=OBSERVED
        )
    else:
        data["cik"] = 999
    with pytest.raises(ValueError, match=r"SHA|issuer"):
        evaluate(data, **args)


@pytest.mark.parametrize(
    "changes",
    [
        {"annual_start": date(2020, 1, 1)},
        {"form": "10-K/A"},
        {"fiscal_focus": "Q4"},
        {"transition": True},
        {"cik": 0},
    ],
)
def test_anchor_refuses_unsupported_declarations(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        anchor(**changes)


def test_observation_requires_aware_time_and_digest() -> None:
    with pytest.raises(ValueError):
        api().SourceObservation(url="source", sha256="a" * 64, observed_at=datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        api().SourceObservation(url="source", sha256="bad", observed_at=OBSERVED)


@given(
    st.permutations(
        [row(100, filed="2019-10-31"), row(100, filed="2020-01-01"), row(25, start="2019-06-30")]
    )
)
def test_anchored_selection_is_row_order_invariant(rows: list[dict[str, object]]) -> None:
    data = base()
    put(data, "Revenues", rows)
    result = evaluate(data)
    assert result.history.years[0].revenue == 100
    assert [fact.row["filed"] for fact in result.selections[0].facts] == [
        "2019-10-31",
        "2020-01-01",
    ]
    with pytest.raises((TypeError, ValueError)):
        result.selections[0].facts[0].row["val"] = 900


@given(ocf=st.integers(-10000, 10000), capex=st.integers(0, 10000), cogs=st.integers(0, 10000))
def test_anchored_derivations_use_only_same_period_operands(
    ocf: int, capex: int, cogs: int
) -> None:
    data = base()
    put(data, "NetCashProvidedByUsedInOperatingActivities", [row(ocf)])
    put(
        data,
        "PaymentsToAcquirePropertyPlantAndEquipment",
        [row(capex), row(99999, start="2019-06-30")],
    )
    put(data, "CostOfRevenue", [row(cogs)])
    year = evaluate(data).history.years[0]
    assert year.free_cash_flow == ocf - capex
    assert year.gross_profit == 100 - cogs


def test_anchored_missing_capex_and_cogs_do_not_become_zero() -> None:
    data = base()
    put(data, "NetCashProvidedByUsedInOperatingActivities", [row(10)])
    year = evaluate(data).history.years[0]
    assert year.free_cash_flow is year.gross_profit is None


def test_anchored_real_frozen_witness_chooses_known_annual() -> None:
    path = (
        Path(__file__).resolve().parents[3]
        / "docs/evidence/FINDING-322/companyfacts.CIK0000320193.20261030.json.gz"
    )
    raw = gzip.decompress(path.read_bytes())
    result = api().evaluate_anchored_fundamentals(
        raw=raw,
        symbol="TEST",
        anchor=anchor(),
        as_of=OBSERVED,
        observation=api().SourceObservation(
            url="source",
            sha256="73a86c6aedc31f77cac2ea4df5f80f0b3bd7e6eb58bb4e01444fbedf3afb9c43",
            observed_at=datetime(2026, 10, 30, 7, 28, 44, 145492, tzinfo=UTC),
        ),
    )
    year = result.history.years[0]
    assert (year.revenue, year.net_income, year.eps) == (260174000000, 55256000000, 11.89)
    assert len(result.history.years) == 1
    assert result.record.combined_score is None


def test_anchored_equal_decimal_spellings_have_order_invariant_exact_claim() -> None:
    data = base()
    put(data, "Revenues", [row(100), row(100.0)])
    first = evaluate(data).selections
    put(data, "Revenues", [row(100.0), row(100)])
    assert evaluate(data).selections == first


def test_anchored_decimal_lexemes_conflict_before_float_rounding() -> None:
    data = base()
    put(data, "Revenues", [row("replace1"), row("replace2")])
    raw = (
        json.dumps(data)
        .replace('"replace1"', "1.00000000000000001")
        .replace('"replace2"', "1.00000000000000002")
        .encode()
    )
    observation = api().SourceObservation(
        url="source", sha256=hashlib.sha256(raw).hexdigest(), observed_at=OBSERVED
    )
    with pytest.raises(ValueError, match="conflicting"):
        evaluate(data, raw=raw, observation=observation)


def test_anchored_direct_gross_profit_precedes_aligned_cogs_fallback() -> None:
    data = base()
    put(data, "GrossProfit", [row(45)])
    put(data, "CostOfRevenue", [row(60)])
    assert evaluate(data).history.years[0].gross_profit == 45


def test_anchored_nonfinite_derived_fcf_refuses() -> None:
    data = base()
    put(data, "NetCashProvidedByUsedInOperatingActivities", [row(1e308)])
    put(data, "PaymentsToAcquirePropertyPlantAndEquipment", [row(-1e308)])
    with pytest.raises(ValueError, match="derived FCF"):
        evaluate(data)


def test_anchored_json_roundtrip_keeps_detached_evidence() -> None:
    data = base()
    result = evaluate(data)
    restored = api().AnchoredEvaluation.model_validate_json(result.model_dump_json())
    assert restored == result
    data["facts"]["us-gaap"]["Revenues"]["units"]["USD"][0]["val"] = 900
    assert restored.history.years[0].revenue == 100
    with pytest.raises((ValueError, TypeError)):
        restored.anchor.header_labels["acceptance"] = "invented"


def test_anchored_unrepresentable_projection_refuses() -> None:
    data = base()
    put(data, "Revenues", [row(10**400)])
    with pytest.raises(ValueError, match="finite"):
        evaluate(data)


def test_anchored_optional_conflict_is_not_missing_or_fallback() -> None:
    data = base()
    put(data, "NetIncomeLoss", [row(10), row(11)])
    with pytest.raises(ValueError, match="conflicting eligible net_income"):
        evaluate(data)
