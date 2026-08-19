"""ValidationEngine (integration): produces a full ValidationReport for a config grid, flags short samples, requires ≥2 configs, and flags overfitting on noise."""

import numpy as np
import pandas as pd
import pytest
from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame
from app.research.strategies.sma import SMAStrategy
from app.validation.engine import ValidationEngine
from app.validation.report import ValidationReport

_CONFIGS = [
    SMAStrategy(fast=f, slow=s)
    for f, s in [(5, 20), (10, 30), (15, 40), (20, 50), (5, 30), (10, 40)]
]


def _random_walk_frame(seed: int, n: int = 300) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    closes = 100.0 * np.cumprod(1 + rng.normal(0, 0.02, n))
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({"close": closes}, index=index)


def test_validation_engine_produces_full_report() -> None:
    # The MVP milestone: Phases 1-4 -> a real ValidationReport for a strategy config grid.
    frame = bars_to_frame(builders.clean_series(n=300))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)

    assert isinstance(report, ValidationReport)
    assert 0.0 <= report.pbo <= 1.0
    assert report.deflated_sharpe <= report.observed_sharpe  # §8 #5
    assert report.n_walk_forward_splits == 5
    assert report.n_purged_folds == 5
    assert isinstance(report.passed, bool)
    # the report serializes for the API/frontend
    assert ValidationReport.model_validate_json(report.model_dump_json()) == report


def test_short_sample_is_flagged() -> None:
    frame = bars_to_frame(builders.clean_series(n=60))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)
    assert any("short sample" in flag for flag in report.flags)


def test_validation_requires_at_least_two_configs() -> None:
    frame = bars_to_frame(builders.clean_series(n=300))
    with pytest.raises(ValueError, match="config"):
        ValidationEngine().validate("sma_crossover", [SMAStrategy()], frame)


def test_overfitting_risk_is_flagged_on_noise() -> None:
    # SMA configs over a random walk have no real edge -> high PBO -> flagged and not passed.
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, _random_walk_frame(seed=0))
    assert report.pbo >= 0.5
    assert any("overfitting" in flag for flag in report.flags)
    assert report.passed is False


def test_report_carries_a_regime_breakdown_for_the_best_config() -> None:
    # ADR-012: the report must surface bull/bear performance of the BEST config so
    # the frontend can say "only works in bulls" when one regime carries the edge.
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, _random_walk_frame(seed=0))
    # Random walk produces both regimes; at least one key should be present.
    assert len(report.regime_breakdown) >= 1
    for label, entry in report.regime_breakdown.items():
        assert label in {"bull", "bear"}
        assert entry.n_bars >= 0


def test_report_carries_a_walk_forward_evaluation() -> None:
    """ADR-038: the splits judge something — they are not just counted."""
    frame = bars_to_frame(builders.clean_series(n=300))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)

    wf = report.walk_forward
    assert wf is not None
    assert wf.n_splits == report.n_walk_forward_splits == 5
    assert len(wf.splits) == 5
    assert all(0 <= s.selected_config < len(_CONFIGS) for s in wf.splits)
    # each window trains on strictly more data than the last, and tests on what follows
    assert [s.n_train for s in wf.splits] == sorted(s.n_train for s in wf.splits)
    assert all(s.n_test > 0 for s in wf.splits)
    assert 0.0 <= wf.consistency <= 1.0
    assert ValidationReport.model_validate_json(report.model_dump_json()) == report


def test_walk_forward_efficiency_is_undefined_when_in_sample_loses() -> None:
    """Pure noise: a ratio of two negative Sharpes would read as 'efficient'. Refuse it."""
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, _random_walk_frame(seed=11))
    wf = report.walk_forward
    assert wf is not None
    assert (wf.efficiency is None) == (wf.mean_is_sharpe <= 0.0)


def test_report_carries_a_purged_cv_evaluation() -> None:
    """ADR-039: the purged folds judge something, and record how hard they were purged."""
    frame = bars_to_frame(builders.clean_series(n=300))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)

    cv = report.purged_cv
    assert cv is not None
    assert cv.n_folds == report.n_purged_folds == 5
    assert all(0 <= f.selected_config < len(_CONFIGS) for f in cv.folds)
    assert cv.oos_sharpe_std >= 0.0
    assert ValidationReport.model_validate_json(report.model_dump_json()) == report


def test_embargo_is_sized_from_the_grid_not_the_constructor_default() -> None:
    """The default embargo of 2 would purge ~1% of a 50-bar strategy's contaminated region."""
    frame = bars_to_frame(builders.clean_series(n=300))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)

    assert report.purged_cv is not None
    assert report.purged_cv.embargo == max(c.parameters["slow"] for c in _CONFIGS)


def test_a_sample_too_short_to_purge_reports_nothing_rather_than_a_leaky_number() -> None:
    """Shrinking the embargo to fit would produce a leaky number labelled 'purged'."""
    frame = bars_to_frame(builders.clean_series(n=60))
    report = ValidationEngine().validate("sma_crossover", _CONFIGS, frame)

    assert report.purged_cv is None
    assert any("purged CV not measured" in flag for flag in report.flags)
