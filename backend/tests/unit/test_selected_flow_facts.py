"""ADR-419 source-row attribution; no vendor/market research calls."""

import gzip
import importlib
import json
from pathlib import Path
from types import ModuleType

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.data.fundamentals import AnnualFundamentals, parse_company_facts_history
from app.research.fundamentals.record import (
    FundamentalRecord,
    compute_fundamental_record,
    merge_fundamental_records,
)

ROOT = Path(__file__).resolve().parents[3]


def api() -> ModuleType:
    return importlib.import_module("app.data.flow_facts")


def row(value: float, start: str = "2024-01-01") -> dict[str, object]:
    return {
        "fy": 2024,
        "fp": "FY",
        "form": "10-K",
        "filed": "2025-02-01",
        "accn": "same-filing",
        "start": start,
        "end": "2024-12-31",
        "val": value,
    }


def payload(rows: list[dict[str, object]]) -> dict[str, object]:
    return {
        "cik": 1,
        "entityName": "Test",
        "facts": {
            "us-gaap": {
                "Revenues": {"units": {"USD": rows}},
            }
        },
    }


@pytest.mark.parametrize(
    "symbol,cik,fy,start,value",
    [
        ("AAPL", "0000320193", 2019, "2019-06-30", 64040000000),
        ("AAPL", "0000320193", 2020, "2020-06-28", 64698000000),
        ("MSFT", "0000789019", 2018, "2018-04-01", 30085000000),
        ("MSFT", "0000789019", 2019, "2019-04-01", 33717000000),
        ("MSFT", "0000789019", 2020, "2020-04-01", 38033000000),
    ],
)
def test_actual_selected_quarters_reach_record_json(
    symbol: str, cik: str, fy: int, start: str, value: int
) -> None:
    facts = json.loads(
        gzip.decompress(
            (
                ROOT / f"docs/evidence/FINDING-322/companyfacts.CIK{cik}.20261030.json.gz"
            ).read_bytes()
        )
    )
    history = parse_company_facts_history(facts, symbol)
    year = next(y for y in history.years if y.fiscal_year == fy)
    flows = year.flow_facts
    assert flows.revenue.tag == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert flows.revenue.unit == "USD"
    assert flows.revenue.row["start"] == start
    assert flows.revenue.row["val"] == value == year.revenue
    assert flows.net_income.row["start"] == start
    assert float(flows.net_income.row["val"]) == year.net_income
    assert flows.eps.unit == "USD/shares"
    assert flows.eps.row["start"] == start
    assert float(flows.eps.row["val"]) == year.eps
    for flow in (flows.revenue, flows.net_income, flows.eps):
        source = facts["facts"]["us-gaap"][flow.tag]["units"][flow.unit]
        assert any({k: r[k] for k in flow.row if k in r} == dict(flow.row) for r in source)
    result = compute_fundamental_record(history)
    stored = FundamentalRecord.model_validate_json(result.model_dump_json())
    retained = next(y for y in stored.flow_fact_history if y.fiscal_year == fy)
    assert retained.facts == flows


def test_original_missing_null_types_and_detached_metadata() -> None:
    raw = row(100.0)
    raw["filed"] = "2025-02-01"
    raw["frame"] = None
    history = parse_company_facts_history(payload([raw]), "T")
    fact = history.years[0].flow_facts.revenue
    assert fact.row["frame"] is None
    assert type(fact.row["fy"]) is int
    assert type(fact.row["val"]) is float
    raw["start"] = "changed"
    assert fact.row["start"] == "2024-01-01"
    with pytest.raises(TypeError):
        fact.row["start"] = "mutated"
    with pytest.raises(ValidationError):
        fact.tag = "changed"
    assert history.years[0].flow_facts.model_dump(mode="json").keys() == {"revenue"}
    no_frame = parse_company_facts_history(payload([row(100.0)]), "T")
    assert "frame" not in no_frame.years[0].flow_facts.revenue.row


def test_first_matching_tag_and_latest_filed_still_bind_same_row() -> None:
    facts = payload([row(100.0), dict(row(200.0), filed="2025-03-01", accn="later")])
    facts["facts"]["us-gaap"]["SalesRevenueNet"] = {"units": {"USD": [row(999.0)]}}
    history = parse_company_facts_history(facts, "T")
    fact = history.years[0].flow_facts.revenue
    assert history.years[0].revenue == 200.0
    assert fact.tag == "Revenues"
    assert fact.row["accn"] == "later"
    assert fact.row["val"] == 200.0


@given(
    st.floats(min_value=1.0, max_value=1e6, allow_nan=False, allow_infinity=False), st.booleans()
)
@settings(max_examples=40, deadline=None)
def test_same_filed_order_moves_value_and_period_together(value: float, reverse: bool) -> None:
    rows = [row(value), row(value / 2, "2024-10-01")]
    if reverse:
        rows.reverse()
    history = parse_company_facts_history(payload(rows), "T")
    selected = history.years[0]
    assert selected.revenue == rows[-1]["val"]
    assert dict(selected.flow_facts.revenue.row) == rows[-1]


def test_direct_legacy_unknown_omission_and_partial_years() -> None:
    history = parse_company_facts_history(payload([row(100.0)]), "T")
    unknown = AnnualFundamentals(fiscal_year=2023, revenue=90.0)
    assert "flow_facts" not in unknown.model_dump(mode="json")
    partial = history.model_copy(update={"years": (unknown, history.years[0])})
    record = compute_fundamental_record(partial)
    assert [y.fiscal_year for y in record.flow_fact_history] == [2023, 2024]
    assert record.flow_fact_history[0].facts is None
    legacy_history = history.model_copy(update={"years": (unknown,)})
    assert "flow_fact_history" not in compute_fundamental_record(legacy_history).model_dump(
        mode="json"
    )
    empty = history.model_copy(update={"years": ()})
    assert "flow_fact_history" not in compute_fundamental_record(empty).model_dump(mode="json")


def test_whole_winner_merge_never_borrows_losing_flow_metadata() -> None:
    known = compute_fundamental_record(parse_company_facts_history(payload([row(100.0)]), "T"))
    legacy = FundamentalRecord.model_validate(known.model_dump(exclude={"flow_fact_history"}))
    winner = merge_fundamental_records([known], [legacy])[0]
    assert "flow_fact_history" not in winner.model_dump(mode="json")
    assert (
        merge_fundamental_records([legacy], [known])[0].flow_fact_history == known.flow_fact_history
    )


def test_evidence_models_revalidate_unchecked_nested_copies() -> None:
    fact = api().SelectedFlowFact(tag="Revenues", unit="USD", row=row(100.0))
    bad = fact.model_copy(update={"row": {"filed": object()}})
    with pytest.raises(ValueError):
        api().SelectedFlowFacts(revenue=bad)
