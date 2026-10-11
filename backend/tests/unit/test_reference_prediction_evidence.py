"""Sign must not conceal malformed present prediction evidence (ADR-233)."""

from itertools import pairwise

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.calibration import oracle_sharpe_of

CLOSES = [100.0, 101.0, 100.0, 101.0, 100.0]


def frame(n: int = 5) -> pd.DataFrame:
    return pd.DataFrame({"close": pd.Series(CLOSES[:n], dtype=float)})


@pytest.mark.parametrize("n", [0, 3, 5])
@pytest.mark.parametrize("bad", [np.inf, -np.inf])
@pytest.mark.parametrize("location", [0, 2, 4])
def test_reference_infinite_present_prediction_is_refused_before_sign(
    n: int, bad: float, location: int
) -> None:
    means = pd.Series([1.0] * 5)
    means.iloc[location] = bad
    with pytest.raises(ValueError, match="predictions must be finite when present"):
        oracle_sharpe_of(frame(n), means)


@pytest.mark.parametrize("n", [0, 3, 5])
@pytest.mark.parametrize("dtype", ["complex128", "bool", "object", "str"])
def test_reference_nonreal_prediction_dtype_is_refused_before_shortcut(n: int, dtype: str) -> None:
    means = pd.Series([1, 2, 1, 2, 1], dtype=dtype)
    with pytest.raises(ValueError, match="predictions must be real nonboolean numeric"):
        oracle_sharpe_of(frame(n), means)


@pytest.mark.parametrize("n", [0, 3, 5])
@pytest.mark.parametrize("dtype", ["float64", "Float64"])
def test_reference_all_missing_numeric_predictions_retain_flat(n: int, dtype: str) -> None:
    means = pd.Series([np.nan] * 5, dtype=dtype)
    assert oracle_sharpe_of(frame(n), means, cost_rate=1e308) == 0.0


@pytest.mark.parametrize("dtype", ["float64", "Float64", "float32", "int64", "Int64"])
@pytest.mark.parametrize("cost", [0.0, 0.001])
def test_reference_valid_numeric_predictions_preserve_exact_native_score(
    dtype: str, cost: float
) -> None:
    data = frame()
    means = pd.Series([0, -1, 1, -1, 1], dtype=dtype)
    returns = data["close"].pct_change().dropna()
    position = np.sign(means.reindex(returns.index)).fillna(0.0)
    earned = position * returns - position.diff().abs().fillna(position.abs()) * cost
    expected = float(np.sqrt(252) * earned.mean() / earned.std())
    assert oracle_sharpe_of(data, means, cost_rate=cost) == expected


@pytest.mark.parametrize("labels", [[1, 3], [8, 9], []])
def test_reference_sparse_unmatched_or_empty_means_keep_flat_alignment(labels: list[int]) -> None:
    data = frame()
    means = pd.Series([1.0] * len(labels), index=labels, dtype=float)
    returns = data["close"].pct_change().dropna()
    position = np.sign(means.reindex(returns.index)).fillna(0.0)
    earned = position * returns - position.diff().abs().fillna(position.abs()) * 0.001
    std = float(earned.std())
    expected = 0.0 if std == 0 else float(np.sqrt(252) * earned.mean() / std)
    assert oracle_sharpe_of(data, means, cost_rate=0.001) == expected


def test_reference_missing_nullable_startup_stays_flat() -> None:
    data = frame()
    means = pd.Series([None, None, -1, 1, -1], dtype="Float64")
    assert oracle_sharpe_of(data, means) == oracle_sharpe_of(data, means.astype(float))


@given(
    st.lists(st.floats(min_value=-1000, max_value=1000, allow_nan=False), min_size=4, max_size=4),
    st.sampled_from([0.0, 0.001]),
)
def test_reference_valid_means_keep_scalar_sign_turnover_and_missing_startup(
    predictions: list[float], cost: float
) -> None:
    means = pd.Series([np.nan, *predictions])
    returns = [right / left - 1.0 for left, right in pairwise(CLOSES)]
    positions = [float((value > 0) - (value < 0)) for value in predictions]
    previous = 0.0
    earned = []
    for position, realized in zip(positions, returns, strict=True):
        earned.append(position * realized - abs(position - previous) * cost)
        previous = position
    std = float(np.std(earned, ddof=1))
    expected = 0.0 if std == 0 else float(np.sqrt(252) * np.mean(earned) / std)
    assert oracle_sharpe_of(frame(), means, cost_rate=cost) == pytest.approx(
        expected, rel=1e-12, abs=1e-12
    )
