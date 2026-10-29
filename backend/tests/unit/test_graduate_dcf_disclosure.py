"""ADR-403: same-winning-row settings, exact count text and legacy unknowns."""

import pytest
from fastapi.testclient import TestClient
from hypothesis import given
from hypothesis import strategies as st
from tests.integration.test_graduates_endpoint import _experiment
from tests.unit.test_valuation_multiples import _three_year

from app.api.v1 import graduates as api
from app.main import app
from app.research.lab.experiment import Experiment, PartitionedExperimentStore
from app.research.lab.universe import rank_experiments
from app.research.valuation.intrinsic_value import DcfAssumptions
from app.research.valuation.score import score_valuation


def _exp(symbol="AAPL", margin=0.3, cap=0.3, horizon=5, scalar=0.5, known=True):
    payload = _experiment(symbol, margin, graduated=True, undervaluation=0.5).model_dump(
        round_trip=True
    )
    score = score_valuation(
        _three_year(), 55.0, assumptions=DcfAssumptions(max_growth=cap, projection_years=horizon)
    )
    raw = score.model_dump(round_trip=True)
    raw.update(symbol=symbol, score=scalar)
    if not known:
        raw.pop("dcf_assumptions")
    payload["undervaluation_score"] = raw
    return Experiment.model_validate(payload)


def _get(pool):
    app.dependency_overrides[api.get_pool_path] = lambda: pool
    try:
        return TestClient(app).get("/api/v1/graduates")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("reverse", [False, True])
def test_internal_carrier_binds_exact_winner_without_changing_leaderboard_wire(
    reverse: bool,
) -> None:
    low, high = _exp(margin=0.2, cap=0.2), _exp(margin=0.4, cap=0.4)
    values = [low, high] if not reverse else [high, low]
    before = [e.model_dump_json() for e in values]
    row = rank_experiments(values)[0]
    assert getattr(row, "dcf_assumptions", None) == high.undervaluation_score.dcf_assumptions
    assert row.deflated_sharpe == 0.4 and row.undervaluation_score == 0.5
    assert (
        "dcf_assumptions" not in row.model_dump() and "dcf_assumptions" not in row.model_dump_json()
    )
    schema = type(row).model_json_schema(mode="serialization")
    assert "dcf_assumptions" not in schema["properties"] and "$defs" not in schema
    assert [e.model_dump_json() for e in values] == before


def test_internal_carrier_preserves_first_tie_and_never_borrows_known_loser_settings() -> None:
    first = _exp(known=False)
    second = _exp(cap=0.4)
    result = rank_experiments([first, second])[0]
    assert getattr(result, "dcf_assumptions", None) is None
    reversed_result = rank_experiments([second, first])[0]
    assert (
        getattr(reversed_result, "dcf_assumptions", None)
        == second.undervaluation_score.dcf_assumptions
    )


@pytest.mark.parametrize(
    "horizon", [0, -2, 5, 9007199254740993, -9007199254740993, 10**100, -(10**100)]
)
@pytest.mark.parametrize("scalar", [None, 0.5])
def test_actual_endpoint_discloses_admitted_horizon_as_exact_text_even_without_scalar(
    tmp_path, horizon: int, scalar: float | None
) -> None:
    pool = tmp_path / "pool"
    source = _exp(horizon=horizon, scalar=scalar)
    store = PartitionedExperimentStore(pool)
    store.add(source)
    original = (pool / "AAPL.json").read_bytes()
    response = _get(pool)
    assert response.status_code == 200
    row = response.json()[0]
    assert row["undervaluation_score"] == scalar
    settings = row.get("dcf_assumptions")
    assert settings is not None
    assert settings == {
        **source.undervaluation_score.dcf_assumptions.model_dump(),
        "projection_years": str(horizon),
    }
    assert (pool / "AAPL.json").read_bytes() == original


def test_endpoint_metadata_and_scalar_come_from_same_ranked_experiment(tmp_path) -> None:
    pool = tmp_path / "pool"
    store = PartitionedExperimentStore(pool)
    store.add(_exp(margin=0.2, cap=0.2, scalar=0.2))
    store.add(_exp(margin=0.4, cap=0.4, scalar=0.4))
    store.add(_exp(symbol="MSFT", margin=0.3, cap=0.3, scalar=0.3))
    rows = _get(pool).json()
    assert [r["symbol"] for r in rows] == ["AAPL", "MSFT"]
    assert [r["undervaluation_score"] for r in rows] == [0.4, 0.3]
    assert [r.get("dcf_assumptions", {}).get("max_growth") for r in rows] == [0.4, 0.3]


def test_legacy_absence_remains_omitted_and_never_becomes_default_settings(tmp_path) -> None:
    pool = tmp_path / "pool"
    PartitionedExperimentStore(pool).add(_exp(known=False))
    row = _get(pool).json()[0]
    assert row["undervaluation_score"] == 0.5
    assert "dcf_assumptions" not in row


@pytest.mark.parametrize(
    "text", ["+1", "-0", "01", "1.0", "1e3", " 1", "1 ", "1\n", "1\r", "1\u2028", "1\u2029", 1]
)
def test_public_view_refuses_noncanonical_horizon_text(text: object) -> None:
    view_type = getattr(api, "DcfSettingsView", None)
    assert view_type is not None, "missing public DCF settings projection"
    with pytest.raises(ValueError):
        view_type(**{**DcfAssumptions().model_dump(), "projection_years": text})


@pytest.mark.parametrize("field", ["discount_rate", "terminal_growth", "min_growth", "max_growth"])
@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -float("inf"), "0.1"])
def test_public_view_refuses_nonfinite_or_reinterpreted_rates(field: str, bad: object) -> None:
    view_type = getattr(api, "DcfSettingsView", None)
    assert view_type is not None, "missing public DCF settings projection"
    with pytest.raises(ValueError):
        view_type(**{**DcfAssumptions().model_dump(), "projection_years": "5", field: bad})


@given(horizon=st.integers(min_value=-(10**100), max_value=10**100))
def test_view_roundtrips_admitted_signed_horizon_without_numeric_projection(horizon: int) -> None:
    view_type = getattr(api, "DcfSettingsView", None)
    assert view_type is not None, "missing public DCF settings projection"
    raw = {
        **DcfAssumptions(min_growth=0.3, max_growth=-0.1).model_dump(),
        "projection_years": str(horizon),
    }
    view = view_type(**raw)
    assert view_type.model_validate_json(view.model_dump_json()).model_dump() == raw
