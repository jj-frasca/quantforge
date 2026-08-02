"""Read-only graduates endpoint: the headline "strategies that cleared the gate" view. Returns
ONLY the research pool's graduated experiments, best-first. Mirrors the lab endpoints — reads the
committed JSON pool with a dependency-injected path so tests feed a synthetic pool (no network/DB)."""

from fastapi.testclient import TestClient

from app.api.v1.graduates import get_pool_path
from app.main import app
from app.research.lab.experiment import Experiment, Graduate, JsonFileExperimentStore, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.valuation import UndervaluationScore


def _gate_result() -> GateResult:
    return GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version="v",
    )


def _experiment(
    symbol: str,
    deflated: float,
    *,
    graduated: bool,
    holdout_sharpe: float = 0.5,
    undervaluation: float | None = None,
) -> Experiment:
    trial = Trial(
        strategy_name="sma",
        parameters={"fast": 10, "slow": 30},
        observed_sharpe=1.0,
        deflated_sharpe=deflated,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    graduate = (
        Graduate(
            strategy_name="sma",
            parameters={"fast": 10, "slow": 30},
            gate_result=_gate_result(),
            holdout_sharpe=holdout_sharpe,
            holdout_total_return=0.1,
            holdout_n_bars=252,
        )
        if graduated
        else None
    )
    score = (
        UndervaluationScore(
            symbol=symbol,
            cik=1,
            entity_name=symbol,
            fiscal_year=2025,
            form="10-K",
            accession_number="x",
            source_url="https://sec.gov/x",
            current_price=100.0,
            pe_ratio=None,
            pe_percentile=None,
            ps_ratio=None,
            ps_percentile=None,
            intrinsic_value_per_share=None,
            margin_of_safety=None,
            growth_rate_used=None,
            fcf_is_net_income_proxy=False,
            score=undervaluation,
            flags=[],
        )
        if undervaluation is not None
        else None
    )
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[trial],
        lifetime_trials=1,
        graduate=graduate,
        undervaluation_score=score,
    )


def test_default_pool_path_points_at_the_in_repo_data_dir() -> None:
    assert get_pool_path().name == "research_pool.json"
    assert get_pool_path().parent.name == "data"


def test_graduates_returns_only_graduated_experiments_best_first(tmp_path) -> None:
    pool = tmp_path / "pool.json"
    store = JsonFileExperimentStore(pool)
    store.add(_experiment("LOW", 0.3, graduated=True))
    store.add(_experiment("CRM", 0.6, graduated=True, undervaluation=0.7))
    store.add(_experiment("SPY", -0.1, graduated=False))
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        body = TestClient(app).get("/api/v1/graduates").json()
        assert [r["symbol"] for r in body] == ["CRM", "LOW"]  # graduates only, best deflated first
        assert body[0]["strategy_name"] == "sma"
        assert body[0]["holdout_sharpe"] == 0.5
        assert body[0]["survives_universe_deflation"] is False
        assert body[0]["undervaluation_score"] == 0.7
        assert body[1]["undervaluation_score"] is None
        # `graduated` is not a field on the graduates view — every row is, by construction.
        assert "graduated" not in body[0]
    finally:
        app.dependency_overrides.clear()


def test_graduates_is_empty_when_pool_file_absent(tmp_path) -> None:
    app.dependency_overrides[get_pool_path] = lambda: tmp_path / "nope.json"
    try:
        assert TestClient(app).get("/api/v1/graduates").json() == []
    finally:
        app.dependency_overrides.clear()


def test_graduates_is_empty_when_no_experiment_graduated(tmp_path) -> None:
    pool = tmp_path / "pool.json"
    JsonFileExperimentStore(pool).add(_experiment("SPY", -0.1, graduated=False))
    app.dependency_overrides[get_pool_path] = lambda: pool
    try:
        assert TestClient(app).get("/api/v1/graduates").json() == []
    finally:
        app.dependency_overrides.clear()
