"""ADR-399: retain supplied history metadata without inventing fact provenance."""

import json
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.unit.test_fundamental_record import _history, _record, _year

from app.research.fundamentals import record as module
from app.research.fundamentals.record import (
    FundamentalRecord,
    compute_fundamental_record,
    load_fundamentals_pool,
    load_fundamentals_shard,
    merge_fundamental_records,
)

FIELDS = ["symbol", "cik", "entity_name", "form", "accession_number", "source_url", "source"]


def _metadata() -> dict:
    return {
        "symbol": "AAA",
        "cik": 1,
        "entity_name": "Supplied Corp",
        "form": "10-K/A",
        "accession_number": "supplied-accession",
        "source_url": "supplied URL",
        "source": "Synthetic source",
    }


def _citation(values: dict | None = None):
    model = getattr(module, "FundamentalHistoryCitation", None)
    assert model is not None, "missing supplied-history citation model"
    return model(**(_metadata() if values is None else values))


def _payload() -> dict:
    return _record("AAA", 1, 2025).model_dump(round_trip=True)


@pytest.mark.parametrize("price", [None, 10.0, 55.0])
@pytest.mark.parametrize("empty", [False, True])
def test_producer_retains_complete_supplied_metadata_even_empty(
    price: float | None, empty: bool
) -> None:
    h = _history("AAA", 1, *(() if empty else (_year(2024), _year(2025))))
    h = h.model_copy(update=_metadata())
    result = compute_fundamental_record(h, price)
    citation = getattr(result, "history_citation", None)
    assert citation is not None, "supplied history metadata was discarded"
    assert citation.model_dump() == _metadata()
    assert FundamentalRecord.model_validate_json(result.model_dump_json()) == result
    if empty:
        assert (
            result.fiscal_year == 0 and result.quality_score is None and result.value_score is None
        )
        assert "no fundamentals history" in result.flags


@pytest.mark.parametrize(
    "field", ["entity_name", "form", "accession_number", "source_url", "source"]
)
def test_each_filing_difference_is_observable_without_score_change(field: str) -> None:
    h = _history("AAA", 1, _year(2024), _year(2025))
    a = compute_fundamental_record(h, 55.0)
    b = compute_fundamental_record(h.model_copy(update={field: f"Changed {field}"}), 55.0)
    assert a.model_dump_json() != b.model_dump_json(), "filing attribution still disappears"
    left, right = a.model_dump(), b.model_dump()
    assert left.pop("history_citation")[field] != right.pop("history_citation")[field]
    assert left == right


@pytest.mark.parametrize("explicit_null", [False, True])
def test_legacy_absence_stays_unknown_and_omitted(explicit_null: bool) -> None:
    payload = _payload()
    original = json.dumps(payload, separators=(",", ":"))
    if explicit_null:
        payload["history_citation"] = None
    result = FundamentalRecord.model_validate(payload)
    assert getattr(result, "history_citation", None) is None
    assert "history_citation" not in result.model_dump(round_trip=True)
    assert result.model_dump_json() == original
    assert FundamentalRecord.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize("field", FIELDS)
def test_present_citation_requires_all_seven_fields(field: str) -> None:
    values = _metadata()
    del values[field]
    model = getattr(module, "FundamentalHistoryCitation", None)
    assert model is not None, "missing supplied-history citation model"
    with pytest.raises(ValidationError, match=field):
        model.model_validate(values)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("bad", [None, 1.5, True, [], {}])
def test_present_citation_refuses_malformed_original_scalars(field: str, bad: object) -> None:
    values = {**_metadata(), field: bad}
    model = getattr(module, "FundamentalHistoryCitation", None)
    assert model is not None, "missing supplied-history citation model"
    with pytest.raises(ValidationError, match=field):
        model.model_validate(values)


def test_citation_forbids_extras_and_integer_coercion() -> None:
    model = type(_citation())
    for values in ({**_metadata(), "unexpected": "evidence"}, {**_metadata(), "cik": "1"}):
        with pytest.raises(ValidationError):
            model.model_validate(values)


@pytest.mark.parametrize("field,changed", [("symbol", "BBB"), ("cik", 2)])
def test_record_binds_citation_company_identity(field: str, changed: object) -> None:
    citation = _citation({**_metadata(), field: changed})
    with pytest.raises(ValidationError, match="history citation must match record symbol and CIK"):
        FundamentalRecord(**_payload(), history_citation=citation)
    with pytest.raises(ValidationError, match="history citation must match record symbol and CIK"):
        FundamentalRecord(**{**_payload(), field: changed}, history_citation=_citation())


def test_citation_is_copied_frozen_and_malformed_instances_revalidate() -> None:
    supplied = _metadata()
    result = FundamentalRecord(**_payload(), history_citation=supplied)
    citation = getattr(result, "history_citation", None)
    assert citation is not None
    supplied["source_url"] = "mutated"
    assert citation.source_url == _metadata()["source_url"]
    with pytest.raises(ValidationError, match="frozen"):
        citation.source_url = "mutated"
    forged = citation.model_copy(update={"source_url": 123})
    with pytest.raises(ValidationError, match="source_url"):
        FundamentalRecord(**_payload(), history_citation=forged)
    invalid = result.model_copy(update={"history_citation": forged})
    with pytest.raises(ValidationError, match="source_url"):
        merge_fundamental_records([], [invalid])


@pytest.mark.parametrize("incoming_year", [2024, 2025, 2026])
@pytest.mark.parametrize("reverse", [False, True])
def test_merge_keeps_whole_winner_citation(incoming_year: int, reverse: bool) -> None:
    a = FundamentalRecord(**_payload(), history_citation=_citation())
    b = FundamentalRecord(
        **{**_payload(), "fiscal_year": incoming_year},
        history_citation=_citation({**_metadata(), "accession_number": "other"}),
    )
    existing, incoming = (b, a) if reverse else (a, b)
    result = merge_fundamental_records([existing], [incoming])[0]
    expected = incoming if incoming.fiscal_year >= existing.fiscal_year else existing
    assert result == expected
    assert getattr(result, "history_citation", None) is not None


def test_legacy_incoming_tie_remains_unknown_without_borrowing_citation() -> None:
    cited = FundamentalRecord(**_payload(), history_citation=_citation())
    unknown = FundamentalRecord(**_payload())
    result = merge_fundamental_records([cited], [unknown])[0]
    assert result == unknown and getattr(result, "history_citation", None) is None
    assert merge_fundamental_records([unknown], [cited])[0] == cited


def test_citation_roundtrips_existing_pool_and_shard_readers(tmp_path: Path) -> None:
    cited = FundamentalRecord(**_payload(), history_citation=_citation())
    unknown = _record("BBB", 2, 2025)
    path = tmp_path / "records.json"
    path.write_text("[" + cited.model_dump_json() + "," + unknown.model_dump_json() + "]")
    assert load_fundamentals_pool(path) == [cited, unknown]
    assert load_fundamentals_shard(path) == [cited, unknown]
    assert getattr(load_fundamentals_pool(path)[0], "history_citation", None) is not None


@given(value=st.text())
def test_supplied_string_metadata_roundtrips_without_normalization(value: str) -> None:
    citation = _citation(
        {**_metadata(), "source_url": value, "source": value, "entity_name": value}
    )
    result = FundamentalRecord(**_payload(), history_citation=citation)
    restored = FundamentalRecord.model_validate_json(result.model_dump_json())
    assert restored.history_citation == citation
    assert restored.history_citation.source_url == value


def test_existing_numeric_refusal_precedes_unchecked_metadata_refusal() -> None:
    h = _history("AAA", 1, _year(2024), _year(2025, net_income=float("inf")))
    h = h.model_copy(update={"source_url": 123})
    with pytest.raises(ValueError, match=r"latest\.net_income must be finite"):
        compute_fundamental_record(h)


def test_producer_refuses_invalid_unchecked_metadata_after_scoring() -> None:
    h = _history("AAA", 1, _year(2024), _year(2025)).model_copy(update={"source_url": 123})
    with pytest.raises(ValidationError, match="source_url"):
        compute_fundamental_record(h)
