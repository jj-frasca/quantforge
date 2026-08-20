"""Universe hunt (ADR-014): run the search across many symbols, resiliently (one bad symbol
never kills the run), and rank the results into a cross-symbol leaderboard. Widening the universe
is the honest way to find edges — trial counts are per-symbol, so more names = more independent
shots, not a bigger overfitting penalty on any one name."""

import math

import numpy as np
import pandas as pd
import pytest

from app.data.fundamentals import FundamentalCriteria, FundamentalSnapshot
from app.research.fundamentals.distress import DistressScreen
from app.research.fundamentals.record import FundamentalRecord
from app.research.lab.experiment import Experiment, Graduate, InMemoryExperimentStore, Trial
from app.research.lab.gate import GateConfig, GateResult
from app.research.lab.quality_filter import QualityGateConfig
from app.research.lab.universe import (
    UniverseHuntResult,
    expected_max_sharpe_under_null,
    rank_experiments,
    run_universe_hunt,
)
from app.research.lab.value_filter import ValueGateConfig
from app.research.valuation import UndervaluationScore

_LENIENT = GateConfig(
    dsr_min=-100.0,
    pbo_max=1.01,
    stability_min=-1.0,
    holdout_sharpe_min=-100.0,
    require_beat_buy_and_hold=False,
)


def _trend(seed: int, drift: float, n: int = 1500) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(drift, 0.01, n))
    idx = pd.date_range("2016-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame({"close": closes}, index=idx)


def _provider(frames: dict[str, pd.DataFrame]):
    def provide(symbol: str) -> pd.DataFrame:
        if symbol not in frames:
            raise ValueError(f"no data for {symbol}")
        return frames[symbol]

    return provide


def test_universe_hunt_runs_every_symbol_and_records_to_the_pool() -> None:
    frames = {"AAA": _trend(1, 0.0005), "BBB": _trend(2, 0.0005)}
    store = InMemoryExperimentStore()
    result = run_universe_hunt(["AAA", "BBB"], ["sma", "momentum"], _provider(frames), store=store)
    assert len(result.experiments) == 2
    assert result.errors == {}
    # Two stored family finalists summarize 7 SMA + 9 momentum configs (ADR-046).
    assert store.trials_for_symbol("AAA") == 16
    assert store.trials_for_symbol("BBB") == 16


def test_a_failing_symbol_is_captured_and_others_still_run() -> None:
    frames = {"GOOD": _trend(1, 0.0005)}  # "BAD" absent -> provider raises
    result = run_universe_hunt(["GOOD", "BAD"], ["sma", "momentum"], _provider(frames))
    assert len(result.experiments) == 1
    assert result.experiments[0].symbol == "GOOD"
    assert "BAD" in result.errors


def test_a_data_normalization_error_is_captured_and_others_still_run() -> None:
    # Regression (prod 2026-07-26): a malformed vendor bar makes the OHLCV normalizer raise
    # decimal.InvalidOperation (an ArithmeticError). One bad symbol must be recorded, not crash.
    from decimal import InvalidOperation

    frames = {"GOOD": _trend(1, 0.0005)}

    def provide(symbol: str) -> pd.DataFrame:
        if symbol == "NANHIGH":
            raise InvalidOperation("[<class 'decimal.ConversionSyntax'>]")
        return frames[symbol]

    result = run_universe_hunt(["GOOD", "NANHIGH"], ["sma", "momentum"], provide)
    assert [e.symbol for e in result.experiments] == ["GOOD"]
    assert "NANHIGH" in result.errors


def test_leaderboard_ranks_graduates_first_then_by_deflated_sharpe() -> None:
    # Strong trend + lenient gate -> both graduate; ranking is by holdout/DSR.
    frames = {"HI": _trend(1, 0.0012), "LO": _trend(2, 0.0011)}
    result = run_universe_hunt(
        ["HI", "LO"], ["sma", "momentum"], _provider(frames), config=_LENIENT
    )
    rows = rank_experiments(result.experiments)
    assert {r.symbol for r in rows} == {"HI", "LO"}
    assert all(r.strategy_name for r in rows)
    # Sorted by (graduated, deflated_sharpe) descending: each row ranks >= the next.
    keys = [(r.graduated, r.deflated_sharpe) for r in rows]
    assert keys == sorted(keys, reverse=True)


def test_fundamentals_provider_applies_the_veto_per_symbol() -> None:
    frames = {"AAA": _trend(1, 0.0012)}
    bad = FundamentalSnapshot(
        symbol="AAA",
        cik=1,
        entity_name="x",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        revenue=1.0,
        revenue_growth_yoy=-0.5,
        net_margin=-0.2,
    )
    result = run_universe_hunt(
        ["AAA"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        fundamentals_provider=lambda s: bad,
        fundamental_criteria=FundamentalCriteria(),
    )
    exp = result.experiments[0]
    assert exp.fundamental_screen is not None and exp.fundamental_screen.passed is False
    assert exp.graduate is None  # vetoed despite lenient technicals


def test_distress_provider_applies_the_veto_per_symbol() -> None:
    frames = {"AAA": _trend(1, 0.0012)}
    result = run_universe_hunt(
        ["AAA"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        distress_provider=lambda s: DistressScreen(distressed=True, reasons=["negative equity"]),
    )
    exp = result.experiments[0]
    assert exp.distress_screen is not None and exp.distress_screen.distressed is True
    assert exp.graduate is None  # vetoed by distress despite lenient technicals


def test_empty_universe_returns_nothing() -> None:
    result = run_universe_hunt([], ["sma"], _provider({}))
    assert result.experiments == []
    assert rank_experiments(result.experiments) == []


def _exp_with_dsr(symbol: str, dsr: float) -> Experiment:
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[
            Trial(
                strategy_name="sma",
                parameters={"fast": 5, "slow": 20},
                observed_sharpe=1.0,
                deflated_sharpe=dsr,
                pbo=0.1,
                parameter_stability_score=0.8,
            )
        ],
        lifetime_trials=1,
    )


def test_leaderboard_collapses_a_symbol_to_its_best_experiment() -> None:
    # A symbol hunted twice -> ONE row (best DSR), so keys are unique + the board isn't padded.
    rows = rank_experiments(
        [_exp_with_dsr("DUP", 0.2), _exp_with_dsr("DUP", 0.5), _exp_with_dsr("OTHER", 0.3)]
    )
    assert len(rows) == 2  # one row per symbol
    dup = [r for r in rows if r.symbol == "DUP"]
    assert len(dup) == 1 and dup[0].deflated_sharpe == 0.5  # kept the better experiment


def test_expected_max_sharpe_under_null_values_and_edges() -> None:
    assert expected_max_sharpe_under_null(1, 4.0) == 0.0  # N<2 -> no selection
    assert expected_max_sharpe_under_null(51, 0.0) == 0.0  # no holdout -> 0
    # N=51, 4y holdout -> sqrt(1/4)*sqrt(2 ln 51) ~= 1.40
    assert expected_max_sharpe_under_null(51, 4.0) == pytest.approx(
        math.sqrt(1 / 4) * math.sqrt(2 * math.log(51))
    )


def _graduated_exp(symbol: str, holdout_sharpe: float, holdout_years: float) -> Experiment:
    trial = Trial(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        observed_sharpe=1.0,
        deflated_sharpe=0.6,
        pbo=0.1,
        parameter_stability_score=0.8,
    )
    gr = GateResult(
        passed=True,
        dsr_ok=True,
        pbo_ok=True,
        stability_ok=True,
        mintrl_ok=True,
        holdout_ok=True,
        required_track_record_years=1.0,
        gate_config_version="v",
    )
    graduate = Graduate(
        strategy_name="sma",
        parameters={"fast": 5, "slow": 20},
        gate_result=gr,
        holdout_sharpe=holdout_sharpe,
        holdout_total_return=0.1,
        holdout_n_bars=int(holdout_years * 252),
    )
    return Experiment(
        symbol=symbol,
        strategy_names=["sma"],
        gate_config=GateConfig(),
        trials=[trial],
        lifetime_trials=1,
        graduate=graduate,
    )


def test_universe_deflation_annotates_graduates() -> None:
    # 51 experiments: a strong graduate (holdout SR 2.0, clears the ~1.4 null bar) survives; a weak
    # one (0.3) does not; non-graduates carry None.
    non_grad = _graduated_exp("PAD", 0.0, 4.0).model_copy(update={"graduate": None})
    experiments = [_graduated_exp("STRONG", 2.0, 4.0), _graduated_exp("WEAK", 0.3, 4.0)]
    experiments += [non_grad.model_copy(update={"symbol": f"N{i}"}) for i in range(49)]
    rows = {r.symbol: r for r in rank_experiments(experiments)}
    assert rows["STRONG"].survives_universe_deflation is True
    assert rows["WEAK"].survives_universe_deflation is False
    assert rows["N0"].survives_universe_deflation is None


def _uscore(symbol: str, score: float | None) -> UndervaluationScore:
    return UndervaluationScore(
        symbol=symbol,
        cik=1,
        entity_name="x",
        fiscal_year=2024,
        form="10-K",
        accession_number="a",
        source_url="http://x",
        current_price=50.0,
        pe_ratio=10.0,
        pe_percentile=0.3,
        ps_ratio=2.0,
        ps_percentile=0.3,
        intrinsic_value_per_share=55.0,
        margin_of_safety=0.1,
        growth_rate_used=0.03,
        fcf_is_net_income_proxy=False,
        score=score,
        flags=[],
    )


def test_value_prescreen_filters_out_names_below_min_score_and_records_the_score() -> None:
    # ADR-023: only hunt names that look undervalued; record the score on the hunted ones.
    frames = {"CHEAP": _trend(1, 0.0012), "RICH": _trend(2, 0.0012)}
    scores = {"CHEAP": _uscore("CHEAP", 0.8), "RICH": _uscore("RICH", 0.1)}
    result = run_universe_hunt(
        ["CHEAP", "RICH"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        value_provider=lambda s: scores[s],
        value_config=ValueGateConfig(min_score=0.5),
    )
    assert [e.symbol for e in result.experiments] == [
        "CHEAP"
    ]  # RICH pre-screened out, never hunted
    assert "RICH" in result.filtered
    recorded = result.experiments[0].undervaluation_score
    assert recorded is not None and recorded.score == 0.8


def test_unscored_name_passes_prescreen_and_records_no_score() -> None:
    # ETF / unmapped ticker -> provider returns None -> hunted on technicals only, score None.
    frames = {"ETF": _trend(1, 0.0012)}
    result = run_universe_hunt(
        ["ETF"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        value_provider=lambda s: None,
        value_config=ValueGateConfig(keep_unscored=True),
    )
    assert [e.symbol for e in result.experiments] == ["ETF"]
    assert result.experiments[0].undervaluation_score is None
    assert result.filtered == {}


def test_value_score_is_recorded_without_prescreen_when_no_value_config() -> None:
    # Recording and pre-screening are separable: a provider without a config records but never filters.
    frames = {"AAA": _trend(1, 0.0012)}
    result = run_universe_hunt(
        ["AAA"],
        ["sma", "momentum"],
        _provider(frames),
        config=_LENIENT,
        value_provider=lambda s: _uscore(
            "AAA", 0.1
        ),  # would fail a screen, but no config -> no screen
    )
    exp = result.experiments[0]
    assert exp.undervaluation_score is not None and exp.undervaluation_score.score == 0.1
    assert result.filtered == {}


def test_value_off_by_default_leaves_the_hunt_unchanged() -> None:
    frames = {"AAA": _trend(1, 0.0012)}
    result = run_universe_hunt(["AAA"], ["sma", "momentum"], _provider(frames), config=_LENIENT)
    assert result.filtered == {}
    assert result.experiments[0].undervaluation_score is None


def test_leaderboard_surfaces_the_undervaluation_score() -> None:
    # ADR-023: the cited undervaluation score recorded on the experiment is surfaced on the row
    # so the dashboard can show "cheap + validated" together. Unscored names carry None.
    scored = _exp_with_dsr("VAL", 0.4).model_copy(
        update={"undervaluation_score": _uscore("VAL", 0.72)}
    )
    unscored = _exp_with_dsr("ETF", 0.3)  # no value score recorded
    rows = {r.symbol: r for r in rank_experiments([scored, unscored])}
    assert rows["VAL"].undervaluation_score == 0.72
    assert rows["ETF"].undervaluation_score is None


def test_leaderboard_undervaluation_score_is_none_when_unscorable() -> None:
    # A recorded score whose composite is None (missing inputs) surfaces as None, not a crash.
    exp = _exp_with_dsr("X", 0.4).model_copy(update={"undervaluation_score": _uscore("X", None)})
    rows = rank_experiments([exp])
    assert rows[0].undervaluation_score is None


def test_rank_skips_experiments_with_no_trials() -> None:
    empty = Experiment(
        symbol="AAA", strategy_names=[], gate_config=GateConfig(), trials=[], lifetime_trials=0
    )
    assert rank_experiments([empty]) == []


# ---- yield_rate: vendor-throttle detection (ADR-031) ----------------------------------------------


def test_yield_rate_is_the_share_of_attempted_symbols_that_produced_an_experiment() -> None:
    result = UniverseHuntResult(
        experiments=[_exp_with_dsr(s, 0.5) for s in ("A", "B", "C")],
        errors={"D": "OSError: Too Many Requests"},
    )
    assert result.yield_rate == 0.75


def test_yield_rate_excludes_deliberately_filtered_names_from_the_denominator() -> None:
    # A name skipped by the ADR-023 value pre-screen was never fetched — counting it as a miss
    # would make a perfectly healthy run look throttled.
    result = UniverseHuntResult(
        experiments=[_exp_with_dsr("A", 0.5)],
        filtered={"B": "too expensive", "C": "too expensive"},
    )
    assert result.yield_rate == 1.0


def test_yield_rate_of_a_total_vendor_wipeout_is_zero() -> None:
    result = UniverseHuntResult(
        experiments=[], errors=dict.fromkeys("ABCDE", "OSError: Too Many Requests")
    )
    assert result.yield_rate == 0.0


def test_yield_rate_is_one_when_nothing_was_attempted() -> None:
    # An empty shard is vacuously fine — a 0/0 must not trip the min-yield floor.
    assert UniverseHuntResult(experiments=[]).yield_rate == 1.0


# ---- ADR-029 4b: the quality pre-screen (opt-in) --------------------------------------------------


def _qrecord(symbol: str, quality: float | None) -> FundamentalRecord:
    return FundamentalRecord(
        symbol=symbol,
        cik=1,
        fiscal_year=2025,
        quality_score=quality,
        value_score=None,
        combined_score=None,
        f_score=6,
        gross_profitability=0.3,
    )


def test_quality_pre_screen_skips_a_low_quality_name_before_it_is_ever_hunted() -> None:
    # Fewer, better-motivated hypotheses is the HONEST way to reduce the ADR-018 deflation N —
    # a screened-out name is never fetched, never searched, and never enters the trial count.
    frames = {"GOOD": _trend(1, 0.0006), "WEAK": _trend(2, 0.0006)}
    fetched: list[str] = []

    def provider(symbol: str) -> pd.DataFrame:
        fetched.append(symbol)
        return frames[symbol]

    records = {"GOOD": _qrecord("GOOD", 0.8), "WEAK": _qrecord("WEAK", 0.1)}
    result = run_universe_hunt(
        ["GOOD", "WEAK"],
        ["sma"],
        provider,
        config=_LENIENT,
        quality_provider=lambda s: records[s],
        quality_config=QualityGateConfig(min_quality_score=0.5),
    )
    assert [e.symbol for e in result.experiments] == ["GOOD"]
    assert "WEAK" in result.filtered
    assert fetched == ["GOOD"]  # the screened name was never even fetched


def test_quality_provider_without_a_config_does_not_filter_anything() -> None:
    # Record-first, like the ADR-023 value wiring: supplying a provider alone must not change which
    # names are hunted. Only an explicit config turns the screen on.
    frames = {"GOOD": _trend(1, 0.0006), "WEAK": _trend(2, 0.0006)}
    records = {"GOOD": _qrecord("GOOD", 0.8), "WEAK": _qrecord("WEAK", 0.1)}
    result = run_universe_hunt(
        ["GOOD", "WEAK"],
        ["sma"],
        _provider(frames),
        config=_LENIENT,
        quality_provider=lambda s: records[s],
    )
    assert {e.symbol for e in result.experiments} == {"GOOD", "WEAK"}
    assert result.filtered == {}


def test_an_unscored_name_survives_the_quality_screen_by_default() -> None:
    frames = {"QQQ": _trend(1, 0.0006)}
    result = run_universe_hunt(
        ["QQQ"],
        ["sma"],
        _provider(frames),
        config=_LENIENT,
        quality_provider=lambda s: None,  # an ETF the EDGAR sweep never scored
        quality_config=QualityGateConfig(min_quality_score=0.9),
    )
    assert [e.symbol for e in result.experiments] == ["QQQ"]
