"""Null-model calibration of the graduation gate (ADR-036). Feed the UNMODIFIED search + gate data
that has no exploitable structure by construction, and count how often it graduates something —
a measured Type-I error for the whole pipeline, which no individual component's guarantee implies.

The two generators answer each other's criticism: `iid_normal_null` is the textbook null (exactly
zero serial dependence, but unrealistically well-behaved), `bootstrap_null` resamples a real
symbol's own bars with replacement (fat tails and gaps preserved exactly, serial dependence
destroyed exactly). Every catalog strategy trades on serial structure, so its true edge on either
is zero.
"""

from datetime import UTC, datetime
from statistics import median

import numpy as np
import pandas as pd
import pytest

from app.research.backtesting.engine import DEFAULT_COST_RATE
from app.research.lab import calibration as calibration_module
from app.research.lab.calibration import (
    NullCalibration,
    NullGraduate,
    NullSymbolDiagnostics,
    PowerCalibration,
    _finalist,
    autocorrelated_edge,
    bootstrap_null,
    calibrate_gate,
    calibration_search_version,
    collect_power_sweep,
    compare_power_sweeps,
    drop_incomplete_bars,
    filtered_deviation,
    iid_normal_null,
    mean_reverting_edge,
    measure_power,
    merge_calibrations,
    oracle_sharpe,
    oracle_sharpe_of,
)
from app.research.lab.experiment import Experiment, Trial
from app.research.lab.gate import GateConfig
from app.research.lab.search import run_search
from app.research.lab.universe import expected_max_sharpe_under_null


def _real_ish_frame(n: int = 900, seed: int = 7) -> pd.DataFrame:
    """A stand-in for a real symbol's history: trending, with a fat-tailed, clustered return
    process — the kind of series `bootstrap_null` is meant to strip the memory out of."""
    rng = np.random.default_rng(seed)
    vol = 0.008 * (1.0 + 0.5 * np.sin(np.linspace(0, 12, n)))  # volatility clustering
    rets = rng.standard_t(4, n) * vol + 0.0004
    closes = 100.0 * np.cumprod(1.0 + rets)
    index = pd.date_range("2016-01-04", periods=n, freq="B", tz="UTC")
    opens = closes * (1.0 + rng.normal(0.0, 0.002, n))
    highs = np.maximum(opens, closes) * (1.0 + np.abs(rng.normal(0.0, 0.004, n)))
    lows = np.minimum(opens, closes) * (1.0 - np.abs(rng.normal(0.0, 0.004, n)))
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": rng.integers(1_000_000, 5_000_000, n).astype(float),
        },
        index=index,
    )


def _lag1(series: pd.Series) -> float:
    return float(series.autocorr(lag=1))


def test_iid_normal_null_is_an_ohlcv_frame_of_the_requested_length() -> None:
    frame = iid_normal_null(600, seed=0)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert len(frame) == 600
    assert frame.index.tz is not None
    assert frame.index.is_monotonic_increasing


def test_null_bars_are_internally_consistent() -> None:
    # A bar whose high is below its close would be rejected by the canonical PriceBar contract;
    # a null the engine can't ingest is not a null of the engine.
    for frame in (iid_normal_null(400, seed=1), bootstrap_null(_real_ish_frame(), 400, seed=1)):
        assert (frame["high"] >= frame[["open", "close"]].max(axis=1) - 1e-9).all()
        assert (frame["low"] <= frame[["open", "close"]].min(axis=1) + 1e-9).all()
        assert (frame[["open", "high", "low", "close"]] > 0).all().all()
        assert (frame["volume"] > 0).all()


def test_iid_normal_null_carries_no_serial_dependence() -> None:
    returns = iid_normal_null(4000, seed=2)["close"].pct_change().dropna()
    assert abs(_lag1(returns)) < 0.05
    # Volatility clustering would show up as autocorrelated |returns| — the classic way a "null"
    # accidentally leaves structure a vol-targeting strategy can trade.
    assert abs(_lag1(returns.abs())) < 0.05


def test_null_generators_are_reproducible_from_their_seed() -> None:
    source = _real_ish_frame()
    pd.testing.assert_frame_equal(iid_normal_null(300, seed=3), iid_normal_null(300, seed=3))
    pd.testing.assert_frame_equal(
        bootstrap_null(source, 300, seed=3), bootstrap_null(source, 300, seed=3)
    )
    assert not iid_normal_null(300, seed=3)["close"].equals(iid_normal_null(300, seed=4)["close"])


def test_bootstrap_null_reuses_only_the_source_returns() -> None:
    # Every resampled return is a value the real symbol actually printed, so the fat tails and the
    # realized drift survive intact — only the ORDER is destroyed. Compared by nearest distance,
    # not equality: the price path is rebuilt by cumprod, so each return round-trips to ~1e-16.
    source = _real_ish_frame()
    reference = np.sort(source["close"].pct_change().dropna().to_numpy())
    sampled = bootstrap_null(source, 500, seed=5)["close"].pct_change().dropna().to_numpy()
    right = np.clip(np.searchsorted(reference, sampled), 1, len(reference) - 1)
    nearest = np.minimum(np.abs(reference[right] - sampled), np.abs(reference[right - 1] - sampled))
    assert nearest.max() < 1e-12


def test_bootstrap_null_destroys_the_source_serial_dependence() -> None:
    source = _real_ish_frame(n=3000)
    sampled = bootstrap_null(source, 3000, seed=6)["close"].pct_change().dropna()
    assert abs(_lag1(sampled.abs())) < 0.05  # the source's vol clustering is gone


def test_bootstrap_null_rejects_a_source_with_no_returns() -> None:
    with pytest.raises(ValueError, match="source"):
        bootstrap_null(_real_ish_frame().iloc[:1], 100, seed=0)


def test_null_generators_reject_a_non_positive_length() -> None:
    with pytest.raises(ValueError, match="n_bars"):
        iid_normal_null(0, seed=0)
    with pytest.raises(ValueError, match="n_bars"):
        bootstrap_null(_real_ish_frame(), 0, seed=0)


def test_calibrate_gate_reports_a_well_formed_false_graduation_rate() -> None:
    frames = {f"NULL{i}": iid_normal_null(760, seed=100 + i) for i in range(4)}
    result = calibrate_gate(frames, ["sma", "momentum"], n_per_param=2)
    assert isinstance(result, NullCalibration)
    assert result.n_symbols == 4
    assert result.n_graduates == len(result.graduate_symbols)
    assert result.false_graduation_rate == pytest.approx(result.n_graduates / 4)
    assert 0.0 <= result.false_graduation_rate <= 1.0
    assert result.deflation_bar > 0.0
    assert result.n_clear_deflation_bar <= result.n_graduates
    assert result.search_config_version != "legacy-unspecified"


def test_the_default_gate_graduates_nothing_from_a_seeded_null_universe() -> None:
    # The scientific assertion, pinned to a seed so it is a regression test: if a future change
    # makes the gate leaky, this goes red. A failure here is a FINDING, not a flaky test —
    # investigate the gate before touching the seed.
    frames = {f"NULL{i}": iid_normal_null(760, seed=200 + i) for i in range(6)}
    result = calibrate_gate(frames, ["sma", "momentum", "rsi_mean_reversion"], n_per_param=2)
    assert result.n_graduates == 0
    assert result.n_clear_deflation_bar == 0


def test_calibration_is_deterministic_for_the_same_null_universe() -> None:
    frames = {f"NULL{i}": iid_normal_null(760, seed=300 + i) for i in range(3)}
    first = calibrate_gate(frames, ["sma"], n_per_param=2)
    second = calibrate_gate(frames, ["sma"], n_per_param=2)
    assert first.model_dump() == second.model_dump()


def test_calibration_search_version_tracks_the_resolved_hypothesis_family() -> None:
    gate = GateConfig()
    baseline = calibration_search_version(["sma"], n_per_param=2, config=gate)

    assert baseline == calibration_search_version(["sma"], n_per_param=2, config=gate)
    assert baseline != calibration_search_version(["sma", "momentum"], n_per_param=2, config=gate)
    assert baseline != calibration_search_version(["sma"], n_per_param=3, config=gate)
    assert baseline != calibration_search_version(["sma"], n_per_param=2, config=gate, refine=False)
    assert baseline != calibration_search_version(
        ["sma"], n_per_param=2, config=gate, refine=True, refine_span=0.10
    )


def test_calibration_search_version_is_order_robust_and_tracks_the_budget() -> None:
    baseline = calibration_search_version(
        ["momentum", "sma", "momentum"], n_per_param=3, config=GateConfig(trial_budget=20)
    )

    assert baseline == calibration_search_version(
        ["sma", "momentum"], n_per_param=3, config=GateConfig(trial_budget=20)
    )
    assert baseline != calibration_search_version(
        ["sma", "momentum"], n_per_param=3, config=GateConfig(trial_budget=21)
    )


def test_calibration_search_version_tracks_trial_accounting_method(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gate = GateConfig()
    baseline = calibration_search_version(["sma"], n_per_param=2, config=gate)
    monkeypatch.setattr(calibration_module, "_TRIAL_ACCOUNTING_VERSION", "test-v2")
    assert baseline != calibration_search_version(["sma"], n_per_param=2, config=gate)


def test_null_and_power_calibration_run_production_refinement_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[bool | None, float | None]] = []
    real_run_search = calibration_module.run_search

    def recording_run_search(*args: object, **kwargs: object) -> object:
        calls.append((kwargs.get("refine"), kwargs.get("refine_span")))
        return real_run_search(*args, **kwargs)

    monkeypatch.setattr(calibration_module, "run_search", recording_run_search)
    calibrate_gate({"NULL": iid_normal_null(760, seed=1)}, ["sma"], n_per_param=2)
    measure_power(
        {"EDGE": autocorrelated_edge(760, seed=1, phi=0.2)},
        ["sma"],
        phi=0.2,
        n_per_param=2,
    )

    assert calls == [(True, 0.25), (True, 0.25)]


def test_calibration_artifacts_expose_the_refinement_policy() -> None:
    null = calibrate_gate(
        {"NULL": iid_normal_null(760, seed=2)},
        ["sma"],
        n_per_param=2,
        refine=False,
    )
    power = measure_power(
        {"EDGE": autocorrelated_edge(760, seed=2, phi=0.2)},
        ["sma"],
        phi=0.2,
        n_per_param=2,
        refine=True,
        refine_span=0.1,
    )

    assert null.refine is False and null.refine_span == pytest.approx(0.25)
    assert power.refine is True and power.refine_span == pytest.approx(0.1)


def test_calibrate_gate_rejects_an_empty_universe() -> None:
    with pytest.raises(ValueError, match="at least"):
        calibrate_gate({}, ["sma"])


def test_a_symbol_that_cannot_be_searched_is_reported_not_silently_dropped() -> None:
    # Too few bars to split into search + holdout. Counting it as a non-graduate would understate
    # the false-graduation rate by inflating the denominator with symbols never actually tested.
    frames = {"OK": iid_normal_null(760, seed=400), "SHORT": iid_normal_null(60, seed=401)}
    result = calibrate_gate(frames, ["sma"], n_per_param=2)
    assert result.n_symbols == 1
    assert list(result.errors) == ["SHORT"]
    assert "insufficient data" in result.errors["SHORT"]


# --- sharding + merge (ADR-037) ---------------------------------------------------------------


def _shard(
    *,
    n_symbols: int = 25,
    graduates: list[NullGraduate] | None = None,
    errors: dict[str, str] | None = None,
    version: str = "v1",
    search_version: str = "search-v1",
    mode: str = "iid_normal",
    max_deflated: float = -0.1,
) -> NullCalibration:
    grads = graduates or []
    return NullCalibration(
        n_symbols=n_symbols,
        n_graduates=len(grads),
        false_graduation_rate=len(grads) / n_symbols,
        n_clear_deflation_bar=0,
        deflation_bar=expected_max_sharpe_under_null(n_symbols, 4.0),
        max_deflated_sharpe=max_deflated,
        max_holdout_sharpe=max((g.holdout_sharpe for g in grads), default=None),
        graduates=grads,
        holdout_years=[4.0] * n_symbols,
        n_bars=[5040] * n_symbols,
        errors=errors or {},
        gate_config_version=version,
        search_config_version=search_version,
        null_mode=mode,
    )


def _graduate(symbol: str, holdout_sharpe: float) -> NullGraduate:
    return NullGraduate(
        symbol=symbol, holdout_sharpe=holdout_sharpe, holdout_n_bars=1008, deflated_sharpe=0.2
    )


def test_merge_sums_the_denominators_and_recomputes_the_rate() -> None:
    merged = merge_calibrations(
        [
            _shard(n_symbols=25, graduates=[_graduate("NULL0001", 1.9)]),
            _shard(n_symbols=25),
            _shard(n_symbols=30),
        ]
    )
    assert merged.n_symbols == 80
    assert merged.n_graduates == 1
    assert merged.false_graduation_rate == pytest.approx(1 / 80)
    assert merged.graduate_symbols == ["NULL0001"]


def test_merge_recomputes_the_deflation_bar_at_the_combined_n() -> None:
    shard = _shard(n_symbols=25)
    merged = merge_calibrations([shard, _shard(n_symbols=25)])
    # The best-of-N bar rises with N: 50 draws under the null beat 25 draws.
    assert merged.deflation_bar > shard.deflation_bar
    assert merged.deflation_bar == pytest.approx(expected_max_sharpe_under_null(50, 4.0))


def test_a_graduate_that_cleared_its_shard_bar_can_fail_the_merged_bar() -> None:
    """The whole reason a shard cannot report a final answer (ADR-037)."""
    lucky = _graduate("NULL0007", 1.60)
    assert lucky.holdout_sharpe > expected_max_sharpe_under_null(8, 4.0)

    merged = merge_calibrations(
        [_shard(n_symbols=8, graduates=[lucky])] + [_shard(n_symbols=8) for _ in range(24)]
    )
    assert merged.n_symbols == 200
    assert lucky.holdout_sharpe < merged.deflation_bar
    assert merged.n_clear_deflation_bar == 0


def test_merge_counts_a_graduate_that_clears_the_merged_bar() -> None:
    merged = merge_calibrations(
        [_shard(n_symbols=25, graduates=[_graduate("NULL0003", 9.0)]), _shard(n_symbols=25)]
    )
    assert merged.n_clear_deflation_bar == 1


def test_merge_refuses_shards_from_different_gate_configs() -> None:
    with pytest.raises(ValueError, match="gate_config_version"):
        merge_calibrations([_shard(version="v1"), _shard(version="v2")])


def test_merge_refuses_shards_from_different_search_spaces() -> None:
    with pytest.raises(ValueError, match="search_config_version"):
        merge_calibrations([_shard(search_version="catalog-a"), _shard(search_version="catalog-b")])


def test_merge_refuses_shards_from_different_null_modes() -> None:
    with pytest.raises(ValueError, match="null_mode"):
        merge_calibrations([_shard(mode="iid_normal"), _shard(mode="bootstrap:AAPL")])


def test_merge_refuses_an_empty_sequence() -> None:
    with pytest.raises(ValueError, match="at least one"):
        merge_calibrations([])


def test_merge_unions_the_errors_and_keeps_the_worst_case_maxima() -> None:
    merged = merge_calibrations(
        [
            _shard(errors={"NULL0001": "too short"}, max_deflated=-0.4),
            _shard(errors={"NULL0099": "too short"}, max_deflated=0.15),
        ]
    )
    assert merged.errors == {"NULL0001": "too short", "NULL0099": "too short"}
    assert merged.max_deflated_sharpe == pytest.approx(0.15)


def test_merging_one_shard_returns_an_equivalent_calibration() -> None:
    shard = _shard(n_symbols=25)
    assert merge_calibrations([shard]).model_dump() == shard.model_dump()


def test_calibrate_gate_records_each_graduate_and_every_holdout_length() -> None:
    frames = {f"NULL{i:03d}": iid_normal_null(700, seed=40 + i) for i in range(3)}
    result = calibrate_gate(frames, ["sma_crossover", "rsi_mean_reversion"], n_per_param=2)
    assert len(result.holdout_years) == result.n_symbols
    assert all(years > 0 for years in result.holdout_years)
    assert len(result.graduates) == result.n_graduates
    assert result.graduate_symbols == [g.symbol for g in result.graduates]
    assert result.null_mode == "unspecified"


def test_calibration_records_the_walk_forward_null_distribution() -> None:
    """ADR-038's revisit trigger: the null run must carry walk-forward numbers to site a floor."""
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(3)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    assert len(result.walk_forward_oos_sharpes) == result.n_symbols
    assert all(isinstance(v, float) for v in result.walk_forward_oos_sharpes)


def test_calibration_pairs_every_null_diagnostic_with_its_symbol() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(3)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    assert [d.symbol for d in result.symbol_diagnostics] == list(frames)
    assert len(result.symbol_diagnostics) == result.n_symbols
    assert [d.walk_forward_oos_sharpe for d in result.symbol_diagnostics] == (
        result.walk_forward_oos_sharpes
    )
    assert [d.walk_forward_hold_sharpe for d in result.symbol_diagnostics] == (
        result.walk_forward_hold_sharpes
    )
    assert [d.purged_cv_oos_sharpe for d in result.symbol_diagnostics] == (
        result.purged_cv_oos_sharpes
    )
    assert [d.purged_cv_hold_sharpe for d in result.symbol_diagnostics] == (
        result.purged_cv_hold_sharpes
    )


def test_paired_artifact_rejects_a_drifting_list_projection() -> None:
    result = calibrate_gate(
        {"NULL0": iid_normal_null(900, seed=0)},
        ["sma", "momentum"],
        null_mode="iid_normal",
    )
    payload = result.model_dump()
    payload["walk_forward_hold_sharpes"] = [result.walk_forward_hold_sharpes[0] + 1.0]

    with pytest.raises(ValueError, match="walk_forward_hold_sharpes"):
        NullCalibration.model_validate(payload)


def test_merging_shards_concatenates_the_walk_forward_distribution() -> None:
    shards = [
        calibrate_gate(
            {f"NULL{i}": iid_normal_null(900, seed=i)}, ["sma", "momentum"], null_mode="iid_normal"
        )
        for i in range(2)
    ]
    merged = merge_calibrations(shards)
    assert merged.walk_forward_oos_sharpes == (
        shards[0].walk_forward_oos_sharpes + shards[1].walk_forward_oos_sharpes
    )


def test_walk_forward_percentiles_site_the_floor_adr_038_would_need() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(4)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    pct = result.walk_forward_null_percentiles
    assert pct is not None
    median_, p95, max_ = pct
    assert median_ <= p95 <= max_
    assert max_ == max(result.walk_forward_oos_sharpes)


def test_walk_forward_percentiles_are_none_when_nothing_was_measured() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(2)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")
    assert (
        result.model_copy(update={"walk_forward_oos_sharpes": []}).walk_forward_null_percentiles
        is None
    )


def test_calibration_records_the_purged_cv_null_distribution() -> None:
    """ADR-039 borrows ADR-038's trigger: measure the statistic under a known-zero edge first."""
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(3)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    assert len(result.purged_cv_oos_sharpes) == result.n_symbols
    pct = result.purged_cv_null_percentiles
    assert pct is not None
    assert pct[0] <= pct[1] <= pct[2]


def test_merging_shards_concatenates_the_purged_cv_distribution() -> None:
    shards = [
        calibrate_gate(
            {f"NULL{i}": iid_normal_null(900, seed=i)}, ["sma", "momentum"], null_mode="iid_normal"
        )
        for i in range(2)
    ]
    merged = merge_calibrations(shards)
    assert merged.purged_cv_oos_sharpes == (
        shards[0].purged_cv_oos_sharpes + shards[1].purged_cv_oos_sharpes
    )


def test_incomplete_bars_are_dropped_so_the_bootstrap_null_is_reproducible() -> None:
    """A calibration is a property of a GateConfig version, so two runs on the same day must agree.
    Including today's in-progress bar made bootstrap:SPY drift between runs while iid_normal was
    bit-identical (runs 32292934031 vs 32297042398)."""
    index = pd.date_range("2026-08-15", periods=5, freq="D", tz=UTC)
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0, 4.0, 5.0]}, index=index)

    trimmed = drop_incomplete_bars(frame, asof=datetime(2026, 8, 19, 14, 0, tzinfo=UTC))

    assert len(trimmed) == 4  # the 2026-08-19 bar is still forming
    assert trimmed.index.max() == pd.Timestamp("2026-08-18", tz=UTC)


def test_dropping_incomplete_bars_leaves_a_settled_frame_untouched() -> None:
    index = pd.date_range("2026-08-10", periods=3, freq="D", tz=UTC)
    frame = pd.DataFrame({"close": [1.0, 2.0, 3.0]}, index=index)
    assert len(drop_incomplete_bars(frame, asof=datetime(2026, 8, 19, tzinfo=UTC))) == 3


def test_dropping_every_bar_is_refused_rather_than_returning_an_empty_frame() -> None:
    index = pd.date_range("2026-08-19", periods=1, freq="D", tz=UTC)
    frame = pd.DataFrame({"close": [1.0]}, index=index)
    with pytest.raises(ValueError, match="no completed bars"):
        drop_incomplete_bars(frame, asof=datetime(2026, 8, 19, tzinfo=UTC))


# --- ADR-041: power. The null says the gate rejects noise; this asks whether it detects an edge ---


def test_autocorrelated_edge_plants_the_requested_serial_dependence() -> None:
    frame = autocorrelated_edge(4000, seed=0, phi=-0.25)
    returns = frame["close"].pct_change().dropna()
    realized = float(returns.autocorr(lag=1))
    assert realized < -0.15  # mean-reverting by construction

    trending = autocorrelated_edge(4000, seed=0, phi=0.25)
    assert float(trending["close"].pct_change().dropna().autocorr(lag=1)) > 0.15


def test_an_edge_frame_is_a_valid_price_frame() -> None:
    frame = autocorrelated_edge(500, seed=1, phi=-0.2)
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert (frame["high"] >= frame[["open", "close"]].max(axis=1)).all()
    assert (frame["low"] <= frame[["open", "close"]].min(axis=1)).all()
    assert (frame["close"] > 0).all()


def test_oracle_sharpe_grows_with_the_planted_effect_size() -> None:
    """The effect size is MEASURED on the same series the search sees — no derivation to get wrong."""
    weak = oracle_sharpe(autocorrelated_edge(3000, seed=2, phi=-0.05), phi=-0.05)
    strong = oracle_sharpe(autocorrelated_edge(3000, seed=2, phi=-0.35), phi=-0.35)
    assert 0.0 < weak < strong


def test_oracle_sharpe_of_a_zero_phi_series_is_not_an_edge() -> None:
    """phi = 0 is the null; the oracle rule has nothing to condition on."""
    assert abs(oracle_sharpe(autocorrelated_edge(3000, seed=3, phi=0.0), phi=0.0)) < 0.5


def test_measure_power_reports_detection_in_two_tiers() -> None:
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    assert result.n_symbols == 3
    assert 0.0 <= result.detection_rate <= 1.0
    assert result.detection_rate == result.n_detected / result.n_symbols
    assert result.n_clear_deflation_bar <= result.n_detected  # the bar is the stricter tier
    assert len(result.oracle_sharpes) == 3
    assert result.phi == -0.3
    assert result.gate_config_version
    assert set(result.gate_pass_counts) == {
        "dsr",
        "pbo",
        "stability",
        "mintrl",
        "holdout",
        "beats_buy_and_hold",
    }
    assert all(0 <= count <= result.n_symbols for count in result.gate_pass_counts.values())


def test_measure_power_refuses_an_empty_universe() -> None:
    with pytest.raises(ValueError, match="at least one"):
        measure_power({}, ["sma", "momentum"], phi=-0.3)


def test_oracle_sharpe_percentiles_summarize_the_planted_effect_size() -> None:
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)
    pct = result.oracle_sharpe_percentiles
    assert pct is not None
    assert pct[0] <= pct[1] <= pct[2]

    assert len(result.finalist_observed_sharpes) == result.n_symbols
    assert result.capture_ratio == pytest.approx(
        np.median(result.finalist_observed_sharpes) / np.median(result.oracle_sharpes)
    )


def test_legacy_power_artifact_has_no_capture_measurement() -> None:
    frames = {"EDGE0": autocorrelated_edge(900, seed=0, phi=-0.3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    legacy = PowerCalibration.model_validate(
        result.model_dump(
            exclude={"finalist_observed_sharpes", "gate_pass_counts", "refine", "refine_span"}
        )
    )

    assert legacy.finalist_observed_sharpes == []
    assert legacy.capture_ratio is None
    assert legacy.gate_pass_counts == {}
    assert legacy.refine is False and legacy.refine_span == pytest.approx(0.25)


def test_legacy_null_artifact_is_labelled_coarse_only() -> None:
    current = calibrate_gate({"NULL": iid_normal_null(760, seed=3)}, ["sma"], n_per_param=2)
    legacy = NullCalibration.model_validate(current.model_dump(exclude={"refine", "refine_span"}))
    assert legacy.refine is False and legacy.refine_span == pytest.approx(0.25)


def test_autocorrelated_edge_rejects_a_non_stationary_phi() -> None:
    with pytest.raises(ValueError, match="stationary"):
        autocorrelated_edge(100, seed=0, phi=1.0)
    with pytest.raises(ValueError, match="n_bars"):
        autocorrelated_edge(0, seed=0, phi=-0.2)


def test_oracle_sharpe_of_a_frame_too_short_to_score_is_zero() -> None:
    frame = autocorrelated_edge(2, seed=0, phi=-0.2)
    assert oracle_sharpe(frame, phi=-0.2) == 0.0


def test_a_symbol_that_cannot_be_searched_is_recorded_and_excluded() -> None:
    """Counting an unsearchable symbol as a non-detection would understate power."""
    frames = {
        "EDGE0": autocorrelated_edge(900, seed=0, phi=-0.3),
        "TOOSHORT": autocorrelated_edge(30, seed=1, phi=-0.3),
    }
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)
    assert result.n_symbols == 1
    assert len(result.finalist_observed_sharpes) == 1
    assert "TOOSHORT" in result.errors


def test_measure_power_refuses_a_universe_where_nothing_can_be_searched() -> None:
    with pytest.raises(ValueError, match="at least one symbol that can be searched"):
        measure_power(
            {"TOOSHORT": autocorrelated_edge(30, seed=0, phi=-0.3)}, ["sma", "momentum"], phi=-0.3
        )


def test_calibrate_gate_refuses_a_universe_where_nothing_can_be_searched() -> None:
    """A universe of unsearchable symbols is a broken run, not a 0% false-graduation rate."""
    with pytest.raises(ValueError, match="at least one null symbol that can be searched"):
        calibrate_gate({"TOOSHORT": iid_normal_null(30, seed=0)}, ["sma", "momentum"])


# --- ADR-042: the same power question, with the reversion HORIZON as the parameter ---


def test_mean_reverting_edge_reverts_at_the_requested_half_life() -> None:
    """A deviation with a 10-bar half-life still shows ~half of itself 10 bars later; a 1-bar one
    is long gone. Measured on the latent deviation, which is what `half_life` is about."""
    slow = mean_reverting_edge(6000, seed=0, half_life=10.0, deviation_share=0.75)
    fast = mean_reverting_edge(6000, seed=0, half_life=1.0, deviation_share=0.75)
    assert slow.deviation.autocorr(lag=10) == pytest.approx(0.5, abs=0.1)
    assert abs(float(fast.deviation.autocorr(lag=10))) < 0.1


def test_mean_reverting_edge_is_mean_reverting_in_returns_at_every_horizon() -> None:
    """The point of the process: whatever the half-life, next-bar returns lean AGAINST the
    deviation. A positive lag-1 return autocorrelation would mean it plants trend, not reversion."""
    for half_life in (1.0, 5.0, 20.0):
        frame = mean_reverting_edge(6000, seed=1, half_life=half_life, deviation_share=0.75).frame
        assert float(frame["close"].pct_change().dropna().autocorr(lag=1)) < 0.0


def test_mean_reverting_edge_holds_total_volatility_across_horizons() -> None:
    """The reason the generator takes a variance SHARE and not a deviation volatility: if realized
    volatility moved with the horizon, every detection rate in the sweep would confound the two."""
    vols = [
        float(
            mean_reverting_edge(6000, seed=2, half_life=h, deviation_share=0.6)
            .frame["close"]
            .pct_change()
            .dropna()
            .std()
        )
        for h in (1.0, 5.0, 20.0)
    ]
    for vol in vols:
        assert vol == pytest.approx(0.012, rel=0.15)


def test_a_mean_reverting_edge_frame_is_a_valid_price_frame() -> None:
    planted = mean_reverting_edge(500, seed=3, half_life=5.0, deviation_share=0.5)
    frame = planted.frame
    assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
    assert (frame["high"] >= frame[["open", "close"]].max(axis=1)).all()
    assert (frame["low"] <= frame[["open", "close"]].min(axis=1)).all()
    assert (frame["close"] > 0).all()
    assert planted.conditional_mean.index.equals(frame.index)


def test_mean_reverting_edge_rejects_impossible_parameters() -> None:
    with pytest.raises(ValueError, match="half_life"):
        mean_reverting_edge(500, seed=0, half_life=0.0, deviation_share=0.5)
    with pytest.raises(ValueError, match="deviation_share"):
        mean_reverting_edge(500, seed=0, half_life=5.0, deviation_share=0.0)
    with pytest.raises(ValueError, match="deviation_share"):
        mean_reverting_edge(500, seed=0, half_life=5.0, deviation_share=1.5)
    with pytest.raises(ValueError, match="n_bars"):
        mean_reverting_edge(0, seed=0, half_life=5.0, deviation_share=0.5)


def test_oracle_sharpe_of_scores_the_conditional_mean_the_engine_could_act_on() -> None:
    """Same rule as ADR-041's AR(1) oracle — sign of E[r_t | F_{t-1}], one-bar lagged — so power
    at a planted half-life is comparable with power at a planted phi."""
    planted = mean_reverting_edge(3000, seed=4, half_life=3.0, deviation_share=0.7)
    assert oracle_sharpe_of(planted.frame, planted.conditional_mean) > 1.0


def test_the_oracle_sharpe_ceiling_falls_as_the_horizon_lengthens() -> None:
    """ADR-042's stated bound: the one-bar-predictable share of the deviation's variance is
    (1-rho)/2, so a slow band cannot be as tradeable as a fast one at the same volatility. This is
    the reason the sweep is read in two tiers, so it is asserted rather than assumed."""
    at_share_one = [
        oracle_sharpe_of(p.frame, p.conditional_mean)
        for p in (
            mean_reverting_edge(4000, seed=5, half_life=h, deviation_share=1.0)
            for h in (1.0, 5.0, 20.0)
        )
    ]
    assert at_share_one[0] > at_share_one[1] > at_share_one[2]


def test_oracle_sharpe_of_a_band_frame_too_short_to_score_is_zero() -> None:
    planted = mean_reverting_edge(2, seed=0, half_life=5.0, deviation_share=0.5)
    assert oracle_sharpe_of(planted.frame, planted.conditional_mean) == 0.0


def test_measure_power_accepts_measured_oracles_for_a_non_ar1_process() -> None:
    planted = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=3.0, deviation_share=0.8)
        for i in range(3)
    }
    result = measure_power(
        {name: p.frame for name, p in planted.items()},
        ["sma", "momentum"],
        oracle_sharpes={
            name: oracle_sharpe_of(p.frame, p.conditional_mean) for name, p in planted.items()
        },
        edge="band_reversion",
        half_life=3.0,
        deviation_share=0.8,
    )
    assert result.phi is None
    assert result.edge == "band_reversion"
    assert result.half_life == 3.0
    assert result.deviation_share == 0.8
    assert len(result.oracle_sharpes) == 3
    assert 0.0 <= result.detection_rate <= 1.0


def test_measure_power_needs_exactly_one_effect_size_source() -> None:
    """Silently defaulting either way would mislabel the effect size of a whole published run."""
    frames = {"BAND0": mean_reverting_edge(900, seed=0, half_life=3.0, deviation_share=0.8).frame}
    with pytest.raises(ValueError, match="phi"):
        measure_power(frames, ["sma"])
    with pytest.raises(ValueError, match="phi"):
        measure_power(frames, ["sma"], phi=-0.2, oracle_sharpes={"BAND0": 1.0})


def test_measure_power_refuses_an_oracle_map_missing_a_searched_symbol() -> None:
    """Dropping the missing symbol would silently shrink the reported effect-size distribution."""
    frames = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=3.0, deviation_share=0.8).frame
        for i in range(2)
    }
    with pytest.raises(ValueError, match="BAND1"):
        measure_power(frames, ["sma"], oracle_sharpes={"BAND0": 1.0})


# --- ADR-051: an artifact must state the history length it was judged at ---


def test_calibration_records_the_bar_count_of_every_searched_symbol() -> None:
    """A null run and a real hunt are only comparable at the same history length, and the length
    was previously recoverable only by knowing the holdout split ratio and multiplying back."""
    frames = {"NULL1": iid_normal_null(800, seed=1), "NULL2": iid_normal_null(900, seed=2)}
    result = calibrate_gate(frames, ["sma"], n_per_param=2)

    assert result.n_bars == [800, 900]
    assert len(result.n_bars) == result.n_symbols


def test_an_unsearchable_symbol_contributes_no_bar_count() -> None:
    """`errors` symbols are excluded from the denominator, so including their length would
    misalign n_bars against holdout_years and every other per-symbol list."""
    frames = {"NULL1": iid_normal_null(800, seed=1), "TOOSHORT": iid_normal_null(20, seed=2)}
    result = calibrate_gate(frames, ["sma"], n_per_param=2)

    assert "TOOSHORT" in result.errors
    assert result.n_bars == [800]


def test_merge_concatenates_the_bar_counts() -> None:
    merged = merge_calibrations([_shard(n_symbols=2), _shard(n_symbols=3)])
    assert len(merged.n_bars) == 5


def test_a_legacy_artifact_states_no_bar_count_rather_than_a_wrong_one() -> None:
    """The 3000-bar artifacts committed before ADR-051 must read back as "unstated", never as the
    new default — that would silently claim they were judged on the hunt's history."""
    legacy = NullCalibration.model_validate_json(
        _shard(n_symbols=2).model_dump_json(exclude={"n_bars"})
    )
    assert legacy.n_bars == []


def test_power_records_the_bar_count_of_every_searched_symbol() -> None:
    """The published zero-power result was measured on 3000 bars against a hunt that gets ~5400.
    A power artifact that does not state its history length cannot be read as a bound on anything
    (ADR-051)."""
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(2)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    assert result.n_bars == [900, 900]
    assert len(result.n_bars) == result.n_symbols


def test_a_legacy_power_artifact_states_no_bar_count() -> None:
    frames = {"EDGE0": autocorrelated_edge(900, seed=0, phi=-0.3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)
    legacy = PowerCalibration.model_validate(result.model_dump(exclude={"n_bars"}))

    assert legacy.n_bars == []


# --- ADR-053: the power sweep as a committed, re-readable record ---


def _power(
    *,
    edge: str = "ar1",
    phi: float | None = -0.2,
    half_life: float | None = None,
    version: str = "v1",
    search_version: str = "search-v1",
    n_bars: int = 5400,
) -> PowerCalibration:
    return PowerCalibration(
        n_symbols=2,
        n_detected=1,
        detection_rate=0.5,
        n_clear_deflation_bar=0,
        deflation_bar=1.5,
        edge=edge,
        phi=phi,
        half_life=half_life,
        oracle_sharpes=[2.0, 2.5],
        holdout_years=[4.3, 4.3],
        n_bars=[n_bars, n_bars],
        errors={},
        gate_config_version=version,
        search_config_version=search_version,
    )


def test_a_power_sweep_sorts_ar1_cells_by_phi() -> None:
    sweep = collect_power_sweep([_power(phi=0.3), _power(phi=-0.3), _power(phi=0.1)])
    assert [c.phi for c in sweep.cells] == [-0.3, 0.1, 0.3]


def test_a_power_sweep_sorts_band_cells_by_half_life() -> None:
    cells = [_power(edge="band_reversion", phi=None, half_life=hl) for hl in (10.0, 1.0, 5.0)]
    sweep = collect_power_sweep(cells)
    assert [c.half_life for c in sweep.cells] == [1.0, 5.0, 10.0]
    assert sweep.edge == "band_reversion"


def test_a_sweep_refuses_to_mix_planted_processes() -> None:
    """An AR(1) cell and a band cell are different experiments; one file holding both would report
    a curve that no single sweep produced."""
    with pytest.raises(ValueError, match="edge"):
        collect_power_sweep([_power(), _power(edge="band_reversion", phi=None, half_life=5.0)])


def test_a_sweep_refuses_cells_measured_by_different_procedures() -> None:
    with pytest.raises(ValueError, match="search_config_version"):
        collect_power_sweep([_power(phi=-0.3), _power(phi=0.3, search_version="search-v2")])


def test_a_sweep_refuses_cells_measured_on_different_histories() -> None:
    """ADR-051: detection rates measured at different bar counts are not points on one curve."""
    with pytest.raises(ValueError, match="n_bars"):
        collect_power_sweep([_power(phi=-0.3), _power(phi=0.3, n_bars=3000)])


def test_an_empty_sweep_is_refused_rather_than_written_as_a_curve() -> None:
    with pytest.raises(ValueError, match="at least one"):
        collect_power_sweep([])


# --- ADR-055: the oracle pays the costs the catalog pays ---


def test_charging_the_oracle_costs_lowers_its_measured_effect_size() -> None:
    """The oracle is a SIGN strategy: it flips between +/-1 and turns over heavily, while every
    catalog finalist it is divided into was charged 10bp on that same turnover."""
    planted = mean_reverting_edge(3000, seed=0, half_life=1.0, deviation_share=0.169)
    gross = oracle_sharpe_of(planted.frame, planted.conditional_mean)
    net = oracle_sharpe_of(planted.frame, planted.conditional_mean, cost_rate=DEFAULT_COST_RATE)

    assert 0.0 < net < gross


def test_the_default_oracle_is_still_the_cost_free_one() -> None:
    """Every committed power artifact was measured gross. A changed default would silently
    restate published effect sizes."""
    planted = mean_reverting_edge(3000, seed=1, half_life=3.0, deviation_share=0.409)
    assert oracle_sharpe_of(planted.frame, planted.conditional_mean) == pytest.approx(
        oracle_sharpe_of(planted.frame, planted.conditional_mean, cost_rate=0.0)
    )


def test_a_fast_flipping_process_loses_more_of_its_edge_to_costs() -> None:
    """The correction is not a constant haircut — it is proportional to how often the oracle has
    to trade, which is exactly what the horizon sweep varies."""
    fast = mean_reverting_edge(3000, seed=2, half_life=1.0, deviation_share=0.169)
    slow = mean_reverting_edge(3000, seed=2, half_life=20.0, deviation_share=0.75)
    fast_loss = oracle_sharpe_of(fast.frame, fast.conditional_mean) - oracle_sharpe_of(
        fast.frame, fast.conditional_mean, cost_rate=DEFAULT_COST_RATE
    )
    slow_loss = oracle_sharpe_of(slow.frame, slow.conditional_mean) - oracle_sharpe_of(
        slow.frame, slow.conditional_mean, cost_rate=DEFAULT_COST_RATE
    )

    assert fast_loss > slow_loss


def test_the_ar1_power_run_records_both_effect_sizes() -> None:
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    assert len(result.net_oracle_sharpes) == 3
    assert result.net_capture_ratio is not None
    assert result.net_capture_ratio == pytest.approx(
        np.median(result.finalist_observed_sharpes) / np.median(result.net_oracle_sharpes)
    )
    # The corrected denominator is smaller, so the corrected capture is larger. This is the
    # denominator being fixed, not the catalog improving.
    assert result.capture_ratio is not None
    assert result.net_capture_ratio > result.capture_ratio


def test_a_supplied_process_can_state_its_own_net_effect_size() -> None:
    planted = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=3.0, deviation_share=0.409)
        for i in range(3)
    }
    frames = {name: p.frame for name, p in planted.items()}
    result = measure_power(
        frames,
        ["sma", "momentum"],
        edge="band_reversion",
        oracle_sharpes={
            n: oracle_sharpe_of(p.frame, p.conditional_mean) for n, p in planted.items()
        },
        net_oracle_sharpes={
            n: oracle_sharpe_of(p.frame, p.conditional_mean, cost_rate=DEFAULT_COST_RATE)
            for n, p in planted.items()
        },
    )

    assert len(result.net_oracle_sharpes) == 3
    assert result.net_oracle_sharpe_percentiles is not None


def test_a_run_that_states_no_net_oracle_reports_no_net_capture() -> None:
    """A partial artifact must refuse the ratio rather than silently change its denominator —
    the same refusal `capture_ratio` already makes."""
    planted = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=3.0, deviation_share=0.409)
        for i in range(3)
    }
    frames = {name: p.frame for name, p in planted.items()}
    result = measure_power(
        frames,
        ["sma", "momentum"],
        edge="band_reversion",
        oracle_sharpes={
            n: oracle_sharpe_of(p.frame, p.conditional_mean) for n, p in planted.items()
        },
    )

    assert result.net_oracle_sharpes == []
    assert result.net_capture_ratio is None
    assert result.net_oracle_sharpe_percentiles is None


def test_a_net_oracle_map_without_a_gross_one_is_refused() -> None:
    frames = {"BAND0": mean_reverting_edge(900, seed=0, half_life=3.0, deviation_share=0.409).frame}
    with pytest.raises(ValueError, match="net_oracle_sharpes"):
        measure_power(frames, ["sma"], phi=-0.2, net_oracle_sharpes={"BAND0": 1.0})


def test_a_legacy_power_artifact_has_no_net_effect_size() -> None:
    frames = {"EDGE0": autocorrelated_edge(900, seed=0, phi=-0.3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    legacy = PowerCalibration.model_validate(result.model_dump(exclude={"net_oracle_sharpes"}))

    assert legacy.net_oracle_sharpes == []
    assert legacy.net_capture_ratio is None


def test_a_negative_cost_rate_is_refused() -> None:
    planted = mean_reverting_edge(900, seed=0, half_life=3.0, deviation_share=0.409)
    with pytest.raises(ValueError, match="cost_rate"):
        oracle_sharpe_of(planted.frame, planted.conditional_mean, cost_rate=-0.001)


def test_a_net_oracle_costs_have_eaten_entirely_has_no_capture_fraction() -> None:
    """At |phi| = 0.10 the net oracle is about zero: there is no achievable edge to express a
    capture fraction of, and a ratio against it would divide by noise."""
    result = _power().model_copy(
        update={
            "oracle_sharpes": [1.3, 1.3],
            "net_oracle_sharpes": [-0.06, 0.02],
            "finalist_observed_sharpes": [0.5, 0.6],
        }
    )
    assert result.capture_ratio is not None
    assert result.net_capture_ratio is None


def test_a_run_missing_one_symbol_net_oracle_is_refused() -> None:
    planted = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=3.0, deviation_share=0.409)
        for i in range(2)
    }
    frames = {name: p.frame for name, p in planted.items()}
    with pytest.raises(ValueError, match="net oracle"):
        measure_power(
            frames,
            ["sma"],
            edge="band_reversion",
            oracle_sharpes={
                n: oracle_sharpe_of(p.frame, p.conditional_mean) for n, p in planted.items()
            },
            net_oracle_sharpes={"BAND0": 1.0},
        )


def test_a_net_oracle_inside_its_own_noise_has_no_capture_fraction() -> None:
    """The refreshed phi = +0.10 cell: net oracle +0.02 over 5400 bars, where a Sharpe's own
    standard error is about 0.22. Dividing by it reported a capture of 2855%, which is a ratio
    against noise dressed as a measurement."""
    result = _power().model_copy(
        update={
            "oracle_sharpes": [1.25, 1.25],
            "net_oracle_sharpes": [0.02, 0.02],
            "finalist_observed_sharpes": [0.62, 0.62],
            "n_bars": [5400, 5400],
        }
    )
    assert result.capture_ratio is not None
    assert result.net_capture_ratio is None


def test_a_net_oracle_well_clear_of_its_noise_still_reports_capture() -> None:
    result = _power().model_copy(
        update={
            "oracle_sharpes": [2.63, 2.63],
            "net_oracle_sharpes": [1.15, 1.15],
            "finalist_observed_sharpes": [1.45, 1.45],
            "n_bars": [5400, 5400],
        }
    )
    assert result.net_capture_ratio == pytest.approx(1.45 / 1.15)


def test_a_cell_that_states_no_history_cannot_bound_its_own_noise() -> None:
    result = _power().model_copy(
        update={
            "net_oracle_sharpes": [1.15, 1.15],
            "finalist_observed_sharpes": [1.45, 1.45],
            "n_bars": [],
        }
    )
    assert result.net_capture_ratio is None


def test_both_capture_ratios_are_serialized_not_recomputed_by_every_reader() -> None:
    """The dashboard was re-deriving this from the raw Sharpe arrays, which is the shadow-validator
    pattern the frontend rules forbid — and it could not have applied the noise refusal above."""
    result = _power().model_copy(
        update={
            "net_oracle_sharpes": [1.15, 1.15],
            "finalist_observed_sharpes": [1.45, 1.45],
            "n_bars": [5400, 5400],
        }
    )
    payload = result.model_dump()

    assert payload["capture_ratio"] == pytest.approx(result.capture_ratio)
    assert payload["net_capture_ratio"] == pytest.approx(result.net_capture_ratio)
    assert PowerCalibration.model_validate(payload).net_capture_ratio == pytest.approx(
        result.net_capture_ratio
    )


def test_a_power_cell_names_the_strategy_that_won_each_symbol() -> None:
    """ADR-057. The capture numerator is an in-sample maximum over the searched grid, so it rises
    when the grid grows even if the added strategy never wins. Without the winner's identity a
    capture change between two sweeps cannot be attributed to the catalog change that motivated it."""
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    assert len(result.finalist_strategy_names) == result.n_symbols
    assert set(result.finalist_strategy_names) <= {"sma", "momentum"}
    assert result.finalist_strategy_counts == {
        name: result.finalist_strategy_names.count(name)
        for name in set(result.finalist_strategy_names)
    }
    assert sum(result.finalist_strategy_counts.values()) == result.n_symbols


def test_the_finalist_names_line_up_with_the_finalist_sharpes() -> None:
    """Index-for-index alignment is what makes the attribution readable against the capture ratio;
    a name list of the right LENGTH but the wrong order would silently misattribute. Pinned against
    the same max-DSR trial `measure_power` sends to the gate, recomputed from the same frame."""
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    for index, (symbol, frame) in enumerate(frames.items()):
        experiment = run_search(
            frame,
            symbol,
            ["sma", "momentum"],
            rationale="ADR-057 alignment check",
        )
        finalist = max(experiment.trials, key=lambda t: t.deflated_sharpe)
        assert result.finalist_strategy_names[index] == finalist.strategy_name
        assert result.finalist_observed_sharpes[index] == pytest.approx(finalist.observed_sharpe)


def test_a_partial_attribution_reports_nothing_rather_than_a_wrong_share() -> None:
    """A legacy artifact predates the field; a truncated one is a bug. Both must read as 'not
    measured' — a share computed over a subset would understate the winner's dominance."""
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(2)}
    result = measure_power(frames, ["sma", "momentum"], phi=-0.3)

    legacy = PowerCalibration.model_validate(result.model_dump(exclude={"finalist_strategy_names"}))
    assert legacy.finalist_strategy_names == []
    assert legacy.finalist_strategy_counts == {}

    truncated = PowerCalibration.model_validate(
        {**result.model_dump(), "finalist_strategy_names": result.finalist_strategy_names[:1]}
    )
    assert truncated.finalist_strategy_counts == {}


def _cell(
    key: float,
    *,
    names: list[str] | None = None,
    finalists: list[float] | None = None,
    detected: int = 0,
    edge: str = "band_reversion",
    n_bars: int = 5400,
    search_version: str = "before",
) -> PowerCalibration:
    """A hand-built power cell — comparison is pure arithmetic over recorded fields, so building
    the cells directly keeps the ADR-057 refusals testable without running 50 searches."""
    finalist_sharpes = finalists if finalists is not None else [1.0, 1.0]
    n = len(finalist_sharpes)
    return PowerCalibration(
        n_symbols=n,
        n_detected=detected,
        detection_rate=detected / n,
        n_clear_deflation_bar=0,
        deflation_bar=1.0,
        edge=edge,
        half_life=key if edge == "band_reversion" else None,
        phi=key if edge == "ar1" else None,
        oracle_sharpes=[2.0] * n,
        net_oracle_sharpes=[2.0] * n,
        finalist_observed_sharpes=finalist_sharpes,
        finalist_strategy_names=names if names is not None else [],
        holdout_years=[4.0] * n,
        n_bars=[n_bars] * n,
        errors={},
        gate_config_version="gate-v1",
        search_config_version=search_version,
    )


def test_a_paired_sweep_reports_the_capture_delta_per_cell() -> None:
    """ADR-057 amendment. The comparison the project kept doing by eye, with the qualifications
    attached to the number rather than remembered alongside it."""
    before = collect_power_sweep([_cell(1.0), _cell(5.0)])
    after = collect_power_sweep(
        [
            _cell(1.0, finalists=[1.2, 1.2], search_version="after"),
            _cell(5.0, finalists=[1.0, 1.0], search_version="after"),
        ]
    )

    rows = compare_power_sweeps(before, after)
    assert [r.key for r in rows] == [1.0, 5.0]
    assert rows[0].net_capture_before == pytest.approx(0.5)
    assert rows[0].net_capture_after == pytest.approx(0.6)
    assert rows[0].net_capture_delta == pytest.approx(0.1)
    assert rows[1].net_capture_delta == pytest.approx(0.0)


def test_a_capture_rise_is_not_attributable_without_the_finalist_names() -> None:
    """The whole point of the amendment: a bigger grid raises an in-sample maximum on its own."""
    before = collect_power_sweep([_cell(1.0)])
    after = collect_power_sweep([_cell(1.0, finalists=[1.6, 1.6], search_version="after")])

    row = compare_power_sweeps(before, after)[0]
    assert row.net_capture_delta > 0
    assert row.attributable is False
    assert "finalist" in (row.reason or "")


def test_an_unchanged_finalist_mix_refuses_attribution_even_when_capture_rises() -> None:
    before = collect_power_sweep([_cell(1.0, names=["sma", "sma"])])
    after = collect_power_sweep(
        [_cell(1.0, names=["sma", "sma"], finalists=[1.6, 1.6], search_version="after")]
    )

    row = compare_power_sweeps(before, after)[0]
    assert row.net_capture_delta > 0
    assert row.attributable is False
    assert "mix" in (row.reason or "")


def test_a_moved_finalist_mix_makes_the_capture_change_attributable() -> None:
    before = collect_power_sweep([_cell(1.0, names=["sma", "sma"])])
    after = collect_power_sweep(
        [
            _cell(
                1.0,
                names=["two_timescale_reversion", "sma"],
                finalists=[1.6, 1.0],
                search_version="after",
            )
        ]
    )

    row = compare_power_sweeps(before, after)[0]
    assert row.attributable is True
    assert row.reason is None
    assert row.finalists_before == {"sma": 2}
    assert row.finalists_after == {"two_timescale_reversion": 1, "sma": 1}


def test_a_cell_on_only_one_side_is_reported_not_dropped() -> None:
    before = collect_power_sweep([_cell(1.0), _cell(5.0)])
    after = collect_power_sweep([_cell(1.0, search_version="after")])

    rows = compare_power_sweeps(before, after)
    assert [r.key for r in rows] == [1.0, 5.0]
    unmatched = rows[1]
    assert unmatched.net_capture_after is None
    assert unmatched.attributable is False
    assert "only" in (unmatched.reason or "")


def test_comparing_sweeps_of_different_processes_or_lengths_is_refused() -> None:
    band = collect_power_sweep([_cell(1.0)])
    ar1 = collect_power_sweep([_cell(0.3, edge="ar1", search_version="after")])
    with pytest.raises(ValueError, match="edge"):
        compare_power_sweeps(band, ar1)

    short = collect_power_sweep([_cell(1.0, n_bars=3000, search_version="after")])
    with pytest.raises(ValueError, match="n_bars"):
        compare_power_sweeps(band, short)


def test_comparing_a_sweep_with_itself_is_refused() -> None:
    """Identical search families cannot produce a capture delta that means anything — the whole
    comparison exists to read a CATALOG change."""
    sweep = collect_power_sweep([_cell(1.0)])
    with pytest.raises(ValueError, match="search_config_version"):
        compare_power_sweeps(sweep, sweep)


def test_the_search_fingerprint_is_stable_across_code_changes() -> None:
    """ADR-058 decision 2 reuses committed calibration artifacts by matching their recorded
    `search_config_version` to the restored catalog's. That only works if the hash is a function of
    the resolved search family and nothing else — a silent drift in how it is computed would let a
    stale artifact be reused under a new number, or force a needless re-dispatch under an old one.
    The literal is a fixed two-name family, so a legitimate CATALOG change does not touch it."""
    assert (
        calibration_search_version(
            ["sma", "momentum"], n_per_param=3, config=GateConfig(), refine=True, refine_span=0.25
        )
        == "b8a2326836973064d20581b449629aa26be30bec31d3c6fad6f2420c433ce470"
    )


def test_a_power_cell_records_the_best_finalist_in_each_catalog_category() -> None:
    """ADR-059. Capture's numerator is 'the best finalist', with nothing requiring the finalist to
    trade the planted process — on fast band reversion it usually does not. The per-category record
    is what separates 'the matched family lost narrowly' from 'it was nowhere near'."""
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "momentum", "mean_reversion"], phi=-0.3)

    by_category = result.finalist_sharpes_by_category
    assert set(by_category) == {"Trend", "Mean Reversion"}
    for sharpes in by_category.values():
        assert len(sharpes) == result.n_symbols
    # The overall finalist is the best of the categories on every symbol, by construction.
    for index, best in enumerate(result.finalist_observed_sharpes):
        assert best == pytest.approx(max(s[index] for s in by_category.values()))


def test_capture_by_category_uses_the_same_net_denominator_and_the_same_refusal() -> None:
    frames = {f"EDGE{i}": autocorrelated_edge(900, seed=i, phi=-0.3) for i in range(3)}
    result = measure_power(frames, ["sma", "mean_reversion"], phi=-0.3)

    net = np.median(result.net_oracle_sharpes)
    for category, sharpes in result.finalist_sharpes_by_category.items():
        assert result.net_capture_by_category[category] == pytest.approx(
            float(np.median(sharpes)) / net
        )

    noise = PowerCalibration.model_validate(
        {**result.model_dump(), "net_oracle_sharpes": [0.001] * result.n_symbols}
    )
    assert noise.net_capture_ratio is None
    assert noise.net_capture_by_category == {}


def test_a_legacy_power_artifact_reports_no_per_category_capture() -> None:
    frames = {"EDGE0": autocorrelated_edge(900, seed=0, phi=-0.3)}
    result = measure_power(frames, ["sma", "mean_reversion"], phi=-0.3)

    legacy = PowerCalibration.model_validate(
        result.model_dump(exclude={"finalist_sharpes_by_category"})
    )
    assert legacy.finalist_sharpes_by_category == {}
    assert legacy.net_capture_by_category == {}


def test_the_filter_recovers_a_deviation_that_dominates_the_series() -> None:
    """ADR-061. The achievable oracle is only a benchmark if the filter actually filters — with the
    deviation carrying almost all the variance, the state is nearly observable and the estimate must
    track it closely. This is the check that the recursion is right, run before any claim rests
    on it."""
    planted = mean_reverting_edge(2000, seed=0, half_life=3.0, deviation_share=0.99)
    rho = 0.5 ** (1.0 / 3.0)
    deviation_vol = 0.012 * np.sqrt(0.99 / (2.0 * (1.0 - rho)))
    level_vol = 0.012 * np.sqrt(1.0 - 0.99)

    estimate = filtered_deviation(
        np.log(planted.frame["close"].astype(float).to_numpy()),
        rho=rho,
        level_vol=level_vol,
        deviation_vol=deviation_vol,
    )
    usable = ~np.isnan(estimate)
    correlation = np.corrcoef(estimate[usable], planted.deviation.to_numpy()[usable])[0, 1]
    assert correlation > 0.85


def test_the_achievable_oracle_is_far_below_the_latent_one_at_a_fast_half_life() -> None:
    """The result ADR-061 exists to record: at half-life 1 the latent-state oracle's edge is not
    recoverable from prices by ANY causal strategy, so a capture ratio against it measures the cost
    of not seeing the future rather than a deficiency of the catalog."""
    fast = mean_reverting_edge(5400, seed=0, half_life=1.0, deviation_share=0.169)
    latent = oracle_sharpe_of(fast.frame, fast.conditional_mean, cost_rate=DEFAULT_COST_RATE)
    achievable = oracle_sharpe_of(
        fast.frame, fast.achievable_conditional_mean, cost_rate=DEFAULT_COST_RATE
    )
    assert latent > 1.0
    assert achievable < 0.5
    assert achievable < latent

    slow = mean_reverting_edge(5400, seed=0, half_life=20.0, deviation_share=0.75)
    slow_achievable = oracle_sharpe_of(
        slow.frame, slow.achievable_conditional_mean, cost_rate=DEFAULT_COST_RATE
    )
    # The gap closes with the horizon — the state becomes easier to see, not more valuable.
    assert slow_achievable > achievable


def test_the_achievable_conditional_mean_is_causal() -> None:
    """It is indexed by the bar it PREDICTS and may use nothing from that bar onward — the same
    contract the latent conditional mean keeps."""
    planted = mean_reverting_edge(600, seed=1, half_life=5.0, deviation_share=0.651)
    log_prices = np.log(planted.frame["close"].astype(float).to_numpy())
    rho = 0.5 ** (1.0 / 5.0)
    kwargs = {
        "rho": rho,
        "level_vol": 0.012 * np.sqrt(1.0 - 0.651),
        "deviation_vol": 0.012 * np.sqrt(0.651 / (2.0 * (1.0 - rho))),
        "drift": 0.0003,
    }
    full = filtered_deviation(log_prices, **kwargs)  # type: ignore[arg-type]
    truncated = filtered_deviation(log_prices[:500], **kwargs)  # type: ignore[arg-type]
    np.testing.assert_allclose(full[:500], truncated, equal_nan=True)


def test_a_cell_records_the_achievable_oracle_and_its_capture() -> None:
    frames = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=5.0, deviation_share=0.651)
        for i in range(3)
    }
    result = measure_power(
        {s: p.frame for s, p in frames.items()},
        ["sma", "mean_reversion"],
        oracle_sharpes={
            s: oracle_sharpe_of(p.frame, p.conditional_mean) for s, p in frames.items()
        },
        net_oracle_sharpes={
            s: oracle_sharpe_of(p.frame, p.conditional_mean, cost_rate=DEFAULT_COST_RATE)
            for s, p in frames.items()
        },
        achievable_oracle_sharpes={
            s: oracle_sharpe_of(p.frame, p.achievable_conditional_mean, cost_rate=DEFAULT_COST_RATE)
            for s, p in frames.items()
        },
        edge="band_reversion",
        half_life=5.0,
    )

    assert len(result.achievable_oracle_sharpes) == result.n_symbols
    assert result.achievable_capture_ratio == pytest.approx(
        float(np.median(result.finalist_observed_sharpes))
        / float(np.median(result.achievable_oracle_sharpes))
    )


def test_an_achievable_oracle_inside_its_own_noise_refuses_a_capture_ratio() -> None:
    """Half-life 1 must land here: an achievable oracle of ~0 has no size to express a fraction of.
    The scale is Lo (2002)'s Sharpe standard error, the same refusal ADR-055 applies to the net
    ratio."""
    frames = {
        f"BAND{i}": mean_reverting_edge(900, seed=i, half_life=5.0, deviation_share=0.651)
        for i in range(2)
    }
    result = measure_power(
        {s: p.frame for s, p in frames.items()},
        ["sma", "mean_reversion"],
        oracle_sharpes=dict.fromkeys(frames, 2.0),
        net_oracle_sharpes=dict.fromkeys(frames, 1.5),
        achievable_oracle_sharpes=dict.fromkeys(frames, 0.01),
        edge="band_reversion",
        half_life=5.0,
    )
    assert result.achievable_capture_ratio is None
    assert result.net_capture_ratio is not None


def test_a_legacy_cell_has_no_achievable_oracle() -> None:
    frames = {"BAND0": mean_reverting_edge(900, seed=0, half_life=5.0, deviation_share=0.651)}
    result = measure_power(
        {s: p.frame for s, p in frames.items()},
        ["sma", "mean_reversion"],
        oracle_sharpes=dict.fromkeys(frames, 2.0),
        edge="band_reversion",
        half_life=5.0,
    )
    assert result.achievable_oracle_sharpes == []
    assert result.achievable_capture_ratio is None


# --- ADR-068: the null carries what holding its own generated series earned ---


def test_the_null_records_what_holding_its_own_series_earned() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(3)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    assert len(result.walk_forward_hold_sharpes) == result.n_symbols


def test_the_null_search_adds_almost_nothing_over_holding_the_same_series() -> None:
    """The point of ADR-068. A null's OOS Sharpe looks like skill until it is read against the
    drift of the series it was measured on, which is where the whole level comes from."""
    frames = {f"NULL{i}": iid_normal_null(1500, seed=i) for i in range(6)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    excess = [
        oos - hold
        for oos, hold in zip(
            result.walk_forward_oos_sharpes, result.walk_forward_hold_sharpes, strict=True
        )
    ]
    assert median(excess) < median(result.walk_forward_oos_sharpes)


def test_merging_shards_concatenates_the_hold_distribution() -> None:
    shards = [
        calibrate_gate(
            {f"NULL{i}": iid_normal_null(900, seed=i)}, ["sma", "momentum"], null_mode="iid_normal"
        )
        for i in range(2)
    ]
    merged = merge_calibrations(shards)

    assert merged.walk_forward_hold_sharpes == (
        shards[0].walk_forward_hold_sharpes + shards[1].walk_forward_hold_sharpes
    )


def test_merging_shards_preserves_symbol_paired_diagnostics() -> None:
    shards = [
        calibrate_gate(
            {f"NULL{i}": iid_normal_null(900, seed=i)},
            ["sma", "momentum"],
            null_mode="iid_normal",
        )
        for i in range(2)
    ]

    merged = merge_calibrations(shards)

    assert merged.symbol_diagnostics == (
        shards[0].symbol_diagnostics + shards[1].symbol_diagnostics
    )


def test_merge_refuses_mixed_paired_and_legacy_shards() -> None:
    paired = _shard(n_symbols=1).model_copy(
        update={
            "symbol_diagnostics": [
                NullSymbolDiagnostics(symbol="NULL0000", n_bars=5040, holdout_years=4.0)
            ]
        }
    )

    with pytest.raises(ValueError, match="paired and legacy"):
        merge_calibrations([paired, _shard(n_symbols=1)])


def test_merge_refuses_duplicate_paired_symbol_identity() -> None:
    diagnostic = NullSymbolDiagnostics(symbol="NULL0000", n_bars=5040, holdout_years=4.0)
    shards = [
        _shard(n_symbols=1).model_copy(update={"symbol_diagnostics": [diagnostic]})
        for _ in range(2)
    ]

    with pytest.raises(ValueError, match="duplicate null symbol"):
        merge_calibrations(shards)


def test_an_artifact_predating_the_benchmark_carries_no_hold_distribution() -> None:
    """ADR-067: absent is not zero — an excess of zero is a measurement nobody made."""
    artifact = NullCalibration(
        n_symbols=1,
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.3,
        max_deflated_sharpe=-0.2,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[4.0],
        n_bars=[5400],
        errors={},
        gate_config_version="v1",
        null_mode="iid_normal",
    )

    assert artifact.walk_forward_hold_sharpes == []


# --- ADR-078: the null carries the purged-CV benchmark too ---


def test_the_null_records_what_holding_its_own_series_earned_across_the_folds() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(3)}
    result = calibrate_gate(frames, ["sma", "momentum"], null_mode="iid_normal")

    assert len(result.purged_cv_hold_sharpes) == result.n_symbols


def test_merging_shards_concatenates_the_purged_hold_distribution() -> None:
    shards = [
        calibrate_gate(
            {f"NULL{i}": iid_normal_null(900, seed=i)}, ["sma", "momentum"], null_mode="iid_normal"
        )
        for i in range(2)
    ]
    merged = merge_calibrations(shards)

    assert merged.purged_cv_hold_sharpes == (
        shards[0].purged_cv_hold_sharpes + shards[1].purged_cv_hold_sharpes
    )


def test_an_artifact_predating_the_purged_benchmark_carries_no_hold_distribution() -> None:
    """ADR-067: absent is not zero."""
    artifact = NullCalibration(
        n_symbols=1,
        n_graduates=0,
        false_graduation_rate=0.0,
        n_clear_deflation_bar=0,
        deflation_bar=1.3,
        max_deflated_sharpe=-0.2,
        max_holdout_sharpe=None,
        graduates=[],
        holdout_years=[4.0],
        n_bars=[5400],
        errors={},
        gate_config_version="v1",
        null_mode="iid_normal",
    )

    assert artifact.purged_cv_hold_sharpes == []


# --- ADR-069: both arms of the selection rule measured by the same code path ---


def test_the_null_can_be_calibrated_under_the_walk_forward_rule() -> None:
    frames = {f"NULL{i}": iid_normal_null(900, seed=i) for i in range(2)}

    default = calibrate_gate(frames, ["sma", "momentum"], n_per_param=2)
    walk = calibrate_gate(frames, ["sma", "momentum"], n_per_param=2, select_by="walk_forward")

    assert walk.search_config_version != default.search_config_version
    assert walk.n_symbols == default.n_symbols


def test_calibration_extracts_the_finalist_selected_by_the_requested_rule() -> None:
    """ADR-071: verdict and diagnostic attribution must describe the same family.

    ADR-069 exists because observed and walk-forward ranking can disagree. Reconstructing every
    calibration finalist as max DSR silently puts the default family's diagnostics into a
    non-default artifact even though another family was sent to the holdout and gate.
    """
    observed_winner = Trial(
        strategy_name="sma",
        parameters={},
        observed_sharpe=2.0,
        deflated_sharpe=1.0,
        pbo=0.1,
        parameter_stability_score=0.8,
        walk_forward_oos_sharpe=0.1,
    )
    walk_forward_winner = Trial(
        strategy_name="momentum",
        parameters={},
        observed_sharpe=1.0,
        deflated_sharpe=0.0,
        pbo=0.1,
        parameter_stability_score=0.8,
        walk_forward_oos_sharpe=0.9,
    )
    experiment = Experiment(
        symbol="TEST",
        strategy_names=["sma", "momentum"],
        gate_config=GateConfig(),
        trials=[observed_winner, walk_forward_winner],
        lifetime_trials=2,
        best_strategy_name="momentum",
    )

    assert _finalist(experiment, "observed") == observed_winner
    assert _finalist(experiment, "walk_forward") == walk_forward_winner


def test_walk_forward_null_diagnostics_describe_the_family_sent_to_the_gate() -> None:
    frame = iid_normal_null(900, seed=0)
    names = ["sma", "momentum", "rsi_mean_reversion"]
    experiment = run_search(frame, "NULL0", names, refine=True, select_by="walk_forward")
    selected = _finalist(experiment, "walk_forward")
    assert selected.strategy_name != _finalist(experiment, "observed").strategy_name

    calibration = calibrate_gate(
        {"NULL0": frame}, names, null_mode="iid_normal", select_by="walk_forward"
    )

    assert calibration.walk_forward_oos_sharpes == [selected.walk_forward_oos_sharpe]
    assert calibration.purged_cv_oos_sharpes == [selected.purged_cv_oos_sharpe]


def test_walk_forward_power_attribution_describes_the_family_sent_to_the_gate() -> None:
    frame = iid_normal_null(900, seed=0)
    names = ["sma", "momentum", "rsi_mean_reversion"]
    experiment = run_search(frame, "EDGE0", names, refine=True, select_by="walk_forward")
    selected = _finalist(experiment, "walk_forward")
    assert selected.strategy_name != _finalist(experiment, "observed").strategy_name

    calibration = measure_power({"EDGE0": frame}, names, phi=-0.3, select_by="walk_forward")

    assert calibration.finalist_strategy_names == [selected.strategy_name]
    assert calibration.finalist_observed_sharpes == [selected.observed_sharpe]


def test_a_power_sweep_records_which_rule_selected_its_finalists() -> None:
    frames = {f"AR{i}": autocorrelated_edge(900, phi=-0.3, seed=i) for i in range(2)}

    walk = measure_power(
        frames, ["sma", "momentum"], phi=-0.3, n_per_param=2, select_by="walk_forward"
    )

    assert walk.search_config_version == calibration_search_version(
        ["sma", "momentum"],
        n_per_param=2,
        config=GateConfig(),
        refine=True,
        select_by="walk_forward",
    )
