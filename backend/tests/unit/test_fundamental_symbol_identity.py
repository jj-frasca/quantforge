"""ADR-371: symbol inputs must not choose or combine different company owners."""

import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scripts import cross_sectional_hunt as driver

from app.research.fundamentals.record import FundamentalRecord, score_maps
from app.research.lab.quality_filter import QualityGateConfig, make_quality_provider
from app.research.lab.universe import run_universe_hunt


def _record(
    symbol: str,
    cik: int,
    year: int = 2025,
    quality: float | None = 0.8,
    value: float | None = 0.2,
) -> FundamentalRecord:
    return FundamentalRecord(
        symbol=symbol,
        cik=cik,
        fiscal_year=year,
        quality_score=quality,
        value_score=value,
        combined_score=None if quality is None or value is None else quality * value,
        f_score=5,
        gross_profitability=0.2,
    )


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("legs", ["complete", "complementary", "absent", "case_alias"])
def test_score_maps_refuses_cross_company_identity_before_filtering_legs(
    reverse: bool, legs: str
) -> None:
    records = [
        _record(
            "DUP",
            1,
            quality=None if legs == "absent" else 0.9,
            value=None if legs in ("complementary", "absent") else 0.3,
        ),
        _record(
            "dup" if legs == "case_alias" else "DUP",
            2,
            quality=None if legs in ("complementary", "absent") else 0.4,
            value=None if legs == "absent" else 0.2,
        ),
    ]
    if reverse:
        records.reverse()
    before = [record.model_dump_json() for record in records]
    with pytest.raises(ValueError, match=r"ambiguous.*DUP"):
        score_maps(records)
    assert [record.model_dump_json() for record in records] == before


@pytest.mark.parametrize("keep_unscored", [False, True])
@pytest.mark.parametrize("scored", [False, True])
def test_quality_provider_refuses_only_requested_ambiguity_before_frame_fetch(
    keep_unscored: bool, scored: bool
) -> None:
    records = [
        _record("DUP", 1, quality=0.9 if scored else None),
        _record("dup", 2, quality=0.8 if scored else None),
        _record("GOOD", 3),
    ]
    provider = make_quality_provider(records)
    assert provider("good") == records[2]
    assert provider("MISSING") is None
    events: list[str] = []

    def earlier_value_provider(symbol: str) -> None:
        events.append("value")
        return None

    def forbidden_frame_provider(symbol: str) -> None:
        raise AssertionError("ambiguous owner must refuse before frame acquisition/search")

    result = run_universe_hunt(
        ["DUP"],
        ["sma"],
        forbidden_frame_provider,
        quality_provider=provider,
        quality_config=QualityGateConfig(keep_unscored=keep_unscored),
        value_provider=earlier_value_provider,
    )
    assert result.experiments == []
    assert result.filtered == {}
    assert "ambiguous" in result.errors["DUP"]
    assert events == ["value"]  # preserve the existing earlier value-provider call


def test_unambiguous_same_company_history_raw_keys_and_missing_scores_remain() -> None:
    old = _record("Mixed", 1, 2024, quality=0.0, value=0.2)
    latest = _record("Mixed", 1, 2025, quality=None, value=0.4)
    other = _record("OTHER", 2, quality=0.5, value=None)
    records = [old, latest, other]
    assert score_maps(records) == ({"Mixed": 0.0, "OTHER": 0.5}, {"Mixed": 0.4})
    provider = make_quality_provider(records)
    assert provider("mixed") == latest
    assert provider("OTHER") == other
    assert score_maps([]) == ({}, {})


def test_score_maps_reports_multiple_ambiguous_symbols_in_sorted_order() -> None:
    records = [_record("ZED", 1), _record("ALPHA", 2), _record("zed", 3), _record("alpha", 4)]
    with pytest.raises(ValueError, match="ambiguous fundamental symbol ownership: ALPHA, ZED"):
        score_maps(records)


class _StopBeforeSearch(Exception):
    pass


def _driver_inputs(
    monkeypatch: pytest.MonkeyPatch, records: list[FundamentalRecord], symbols: list[str]
) -> dict[str, object]:
    captured: dict[str, object] = {}
    monkeypatch.setattr(sys, "argv", ["cross_sectional_hunt.py", *symbols])
    monkeypatch.setattr(driver, "YFinanceAdapter", lambda **kwargs: object())
    monkeypatch.setattr(driver, "JsonFileCrossSectionalStore", lambda *args: object())
    monkeypatch.setattr(driver, "current_git_revision", lambda: "a" * 40)
    monkeypatch.setattr(driver, "load_fundamentals_pool", lambda path: records)

    def capture(*args: object, **kwargs: object) -> None:
        captured.update(kwargs)
        raise _StopBeforeSearch

    monkeypatch.setattr(driver, "run_cross_sectional_hunt", capture)
    return captured


def test_driver_ignores_unrequested_ambiguity_and_projects_only_requested_scores(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [_record("DUP", 1), _record("DUP", 2), _record("KEEP", 3)]
    captured = _driver_inputs(monkeypatch, records, ["KEEP"])
    with pytest.raises(_StopBeforeSearch):
        driver.main()
    assert captured["quality_scores"] == {"KEEP": 0.8}
    assert captured["value_scores"] == {"KEEP": 0.2}


def test_driver_refuses_requested_ambiguity_before_any_hunt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records = [_record("DUP", 1), _record("dup", 2)]
    captured = _driver_inputs(monkeypatch, records, ["DUP"])
    with pytest.raises(ValueError, match=r"ambiguous.*DUP"):
        driver.main()
    assert captured == {}


@pytest.mark.parametrize("quality,value", [(0.0, 0.0), (0.8, None), (None, 0.2), (None, None)])
def test_driver_preserves_global_supplied_legs_without_requested_coverage(
    monkeypatch: pytest.MonkeyPatch, quality: float | None, value: float | None
) -> None:
    captured = _driver_inputs(
        monkeypatch, [_record("OUTSIDE", 1, quality=quality, value=value)], ["KEEP"]
    )
    with pytest.raises(_StopBeforeSearch):
        driver.main()
    assert captured["quality_scores"] == ({} if quality is not None else None)
    assert captured["value_scores"] == ({} if value is not None else None)


@settings(max_examples=30, deadline=None)
@given(
    cik=st.integers(min_value=1, max_value=10**6),
    quality=st.floats(min_value=0, max_value=1, allow_nan=False),
    value=st.floats(min_value=0, max_value=1, allow_nan=False),
    reverse=st.booleans(),
)
def test_cross_company_composite_cannot_be_synthesized_by_record_order(
    cik: int, quality: float, value: float, reverse: bool
) -> None:
    records = [
        _record("DUP", cik, quality=quality, value=None),
        _record("DUP", cik + 1, quality=None, value=value),
    ]
    assert all(record.combined_score is None for record in records)
    if reverse:
        records.reverse()
    with pytest.raises(ValueError, match=r"ambiguous.*DUP"):
        score_maps(records)
