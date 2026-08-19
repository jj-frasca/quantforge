"""Null-model calibration of the graduation gate (ADR-036). Feed the UNMODIFIED search + gate data
that has no exploitable structure by construction, and count how often it graduates something —
a measured Type-I error for the whole pipeline, which no individual component's guarantee implies.

The two generators answer each other's criticism: `iid_normal_null` is the textbook null (exactly
zero serial dependence, but unrealistically well-behaved), `bootstrap_null` resamples a real
symbol's own bars with replacement (fat tails and gaps preserved exactly, serial dependence
destroyed exactly). Every catalog strategy trades on serial structure, so its true edge on either
is zero.
"""

import numpy as np
import pandas as pd
import pytest

from app.research.lab.calibration import (
    NullCalibration,
    bootstrap_null,
    calibrate_gate,
    iid_normal_null,
)


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
