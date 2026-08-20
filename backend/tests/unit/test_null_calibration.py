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

import numpy as np
import pandas as pd
import pytest

from app.research.lab import calibration as calibration_module
from app.research.lab.calibration import (
    NullCalibration,
    NullGraduate,
    PowerCalibration,
    autocorrelated_edge,
    bootstrap_null,
    calibrate_gate,
    calibration_search_version,
    drop_incomplete_bars,
    iid_normal_null,
    mean_reverting_edge,
    measure_power,
    merge_calibrations,
    oracle_sharpe,
    oracle_sharpe_of,
)
from app.research.lab.gate import GateConfig
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
