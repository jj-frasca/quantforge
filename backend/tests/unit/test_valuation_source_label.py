"""ADR-400: retain supplied source metadata without changing valuation arithmetic."""

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from tests.unit.test_valuation_multiples import _three_year

from app.research.lab.universe import run_universe_hunt
from app.research.lab.value_filter import ValueGateConfig, make_value_provider
from app.research.valuation.score import UndervaluationScore, score_valuation


@pytest.mark.parametrize(
    "source", ["Synthetic supplied source", "", "SEC EDGAR", '\u03b1\nquoted "source"']
)
@pytest.mark.parametrize("price", [0.0, 10.0, 55.0])
def test_direct_producer_retains_exact_supplied_source(source: str, price: float) -> None:
    h = _three_year().model_copy(update={"source": source})
    result = score_valuation(h, price)
    assert result.source == source
    restored = UndervaluationScore.model_validate_json(result.model_dump_json())
    assert restored.source == source and restored == result
    old = score_valuation(_three_year(), price).model_dump(round_trip=True)
    new = result.model_dump(round_trip=True)
    assert old.pop("source") == "SEC EDGAR" and new.pop("source") == source
    assert old == new


@given(source=st.text())
def test_source_string_roundtrips_without_normalization(source: str) -> None:
    h = _three_year().model_copy(update={"source": source})
    result = score_valuation(h, 55.0)
    assert result.source == source
    assert UndervaluationScore.model_validate_json(result.model_dump_json()).source == source


@pytest.mark.parametrize("source", ["Synthetic provider source", "", "SEC EDGAR"])
def test_real_provider_retains_source_after_acquisition(source: str) -> None:
    h = _three_year().model_copy(update={"source": source})
    events: list[str] = []

    def history(symbol: str):
        events.append("history")
        return h

    def prices(symbol: str):
        events.append("prices")
        return [(date(2025, 12, 31), 55.0)]

    result = make_value_provider(history, prices)(h.symbol)
    assert result is not None and result.source == source
    assert events == ["history", "prices"]


def test_direct_model_default_and_legacy_json_remain_sec_edgar() -> None:
    payload = score_valuation(_three_year(), 55.0).model_dump(round_trip=True)
    explicit = UndervaluationScore.model_validate(payload)
    del payload["source"]
    implicit = UndervaluationScore.model_validate(payload)
    assert implicit.source == "SEC EDGAR" and implicit == explicit
    assert UndervaluationScore.model_validate_json(implicit.model_dump_json()) == explicit


@pytest.mark.parametrize("source", [None, 123, [], {}, float("nan")])
def test_unchecked_invalid_source_refuses_final_validation(source: object) -> None:
    h = _three_year().model_copy(update={"source": source})
    with pytest.raises(ValidationError, match="source"):
        score_valuation(h, 55.0)


def test_earlier_multiple_refusal_precedes_invalid_source() -> None:
    h = _three_year()
    latest = h.years[-1].model_copy(update={"eps": float("nan")})
    h = h.model_copy(update={"years": (*h.years[:-1], latest), "source": None})
    with pytest.raises(ValueError, match="current P/E must be finite"):
        score_valuation(h, 55.0)


@pytest.mark.parametrize("enabled", [False, True])
def test_invalid_source_provider_error_is_not_missingness_or_search(enabled: bool) -> None:
    h = _three_year().model_copy(update={"source": None})
    events: list[str] = []

    def history(symbol: str):
        events.append("history")
        return h

    def prices(symbol: str):
        events.append("prices")
        return [(date(2025, 12, 31), 55.0)]

    provider = make_value_provider(history, prices)
    with pytest.raises(ValidationError, match="source"):
        provider(h.symbol)
    assert events == ["history", "prices"]
    events.clear()

    def downstream(symbol: str):
        events.append("downstream")
        raise ValueError("DOWNSTREAM_SENTINEL_NO_SEARCH")

    result = run_universe_hunt(
        [h.symbol],
        ["sma"],
        downstream,
        value_provider=provider,
        value_config=ValueGateConfig() if enabled else None,
    )
    assert "source" in result.errors[h.symbol]
    assert result.filtered == {} and result.experiments == []
    assert events == ["history", "prices"]
