"""ADR-331: scalar integer classes cannot erase the existing lookback proxy."""

from fractions import Fraction
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.strategies.sma import SMAStrategy
from app.validation.engine import ValidationEngine
from app.validation.purged_cv import lookback_embargo
from app.validation.report import ValidationReport

INTEGER_TYPES = [np.int8, np.int16, np.int32, np.int64, np.uint8, np.uint16, np.uint32, np.uint64]


@pytest.mark.parametrize("dtype", INTEGER_TYPES)
def test_numpy_integer_windows_keep_the_largest_proxy(dtype: Any) -> None:
    configs = [SMAStrategy(dtype(3), dtype(50)), SMAStrategy(dtype(5), dtype(60))]
    result = lookback_embargo(configs, floor=2)
    assert result == 60
    assert type(result) is int


@pytest.mark.parametrize("dtype", INTEGER_TYPES)
def test_maximum_integer_parameter_is_normalized_without_wrap(dtype: Any) -> None:
    maximum = dtype(np.iinfo(dtype).max)
    configs: Any = [SimpleNamespace(parameters={"window": maximum})]
    result = lookback_embargo(configs, floor=2)
    assert result == int(maximum)
    assert type(result) is int


def test_signed_numpy_grid_matches_the_entire_native_validation_report() -> None:
    rng = np.random.default_rng(0)
    frame = pd.DataFrame(
        {"close": 100 * np.cumprod(1 + rng.normal(0.0002, 0.01, 300))},
        index=pd.date_range("2024-01-01", periods=300, tz="UTC"),
    )
    native = [SMAStrategy(3, 50), SMAStrategy(5, 60)]
    typed = [SMAStrategy(np.int64(3), np.int64(50)), SMAStrategy(np.int64(5), np.int64(60))]
    for original, numpy_config in zip(native, typed, strict=True):
        pd.testing.assert_series_equal(
            original.generate_signals(frame), numpy_config.generate_signals(frame)
        )
    expected = ValidationEngine().validate("sma_crossover", native, frame)
    actual = ValidationEngine().validate("sma_crossover", typed, frame)
    assert expected.purged_cv is not None
    assert expected.purged_cv.embargo == 60
    assert actual == expected
    assert ValidationReport.model_validate_json(actual.model_dump_json()) == expected


@pytest.mark.parametrize(
    "ignored", [True, False, np.bool_(True), 50.0, np.float64(50), Fraction(50), "50", None]
)
def test_noninteger_parameter_types_remain_ignored(ignored: Any) -> None:
    configs: Any = [SimpleNamespace(parameters={"threshold": ignored, "window": 7})]
    assert lookback_embargo(configs, floor=2) == 7


def test_original_floor_operand_and_negative_parameter_policy_remain() -> None:
    floor = np.uint64(80)
    configs: Any = [SimpleNamespace(parameters={"negative": np.int64(-90), "window": 50})]
    assert lookback_embargo(configs, floor=floor) is floor
    assert lookback_embargo([], floor=0) == 0
    with pytest.raises(ValueError, match="floor must be >= 0"):
        lookback_embargo(configs, floor=-1)


@given(
    values=st.lists(st.integers(-127, 127), min_size=1, max_size=12),
    dtype=st.sampled_from(INTEGER_TYPES),
    floor=st.integers(0, 200),
)
def test_integral_proxy_matches_original_integer_maximum(
    values: list[int],
    dtype: Any,
    floor: int,
) -> None:
    # Unsigned values keep the same nonnegative mathematical request.
    originals = [
        abs(value) if np.issubdtype(dtype, np.unsignedinteger) else value for value in values
    ]
    configs: Any = [
        SimpleNamespace(
            parameters={
                **{str(i): dtype(value) for i, value in enumerate(originals)},
                "ignored_float": 10_000.0,
                "ignored_bool": True,
            }
        )
    ]
    with np.errstate(all="raise"):
        actual = lookback_embargo(configs, floor=floor)
    assert actual == max([floor, *originals])
