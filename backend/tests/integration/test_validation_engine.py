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
