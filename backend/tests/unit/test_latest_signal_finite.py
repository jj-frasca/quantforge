"""Reject undefined generated paper weights before they acquire a direction (ADR-339)."""

import math
import struct
from datetime import UTC, datetime
from decimal import Decimal
from fractions import Fraction
from unittest.mock import patch

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scripts.paper_broker import compute_targets

from app.data.models import DataQualityReport
from app.execution import sizing
from app.research.dataset import ResearchDataset
from app.research.lab.paper import PaperPosition


def _position() -> PaperPosition:
    return PaperPosition(
        symbol="TEST",
        strategy_name="sma",
        parameters={"fast": 2, "slow": 4},
        frozen_at=datetime(2024, 1, 1, tzinfo=UTC),
    )


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {"close": [100.0] * 8},
        index=pd.date_range("2024-01-01", periods=8, tz="UTC"),
    )


class _Output:
    def __init__(self, value: object) -> None:
        self.value = value

    def generate_signals(self, frame: pd.DataFrame) -> pd.Series:
        # Earlier warmup NaNs remain outside the latest-only boundary.
        return pd.Series(
            [float("nan")] * (len(frame) - 1) + [self.value], index=frame.index, dtype=object
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        np.float32("nan"),
        np.float64("nan"),
        "NaN",
        "Infinity",
        "-Infinity",
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_latest_signal_nonfinite_converted_weight_raises(value: object) -> None:
    with (
        patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)),
        pytest.raises(ValueError, match="latest strategy signal must be finite"),
    ):
        sizing.latest_signal(_position(), _frame())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_quote_position_nonfinite_weight_never_becomes_directional_quote(value: float) -> None:
    with (
        patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)),
        pytest.raises(ValueError, match="latest strategy signal must be finite"),
    ):
        sizing.quote_position(_position(), _frame())


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_compute_targets_nonfinite_derived_weight_aborts_even_with_passed_source(
    value: float,
) -> None:
    dataset = ResearchDataset(
        frame=_frame(),
        quality_report=DataQualityReport(
            symbol="TEST", source="yfinance", checked_at=datetime(2024, 1, 9, tzinfo=UTC)
        ),
        source="yfinance",
        adapter_version="synthetic-test",
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 9, tzinfo=UTC),
        git_commit_hash="a" * 40,
    )
    with (
        patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)),
        pytest.raises(ValueError, match="latest strategy signal must be finite"),
    ):
        compute_targets([_position()], lambda _symbol: dataset, equity=10_000.0)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0.0, 0.0),
        (-0.0, -0.0),
        (1.0, 1.0),
        (-1.0, -1.0),
        (math.nextafter(1.0, 0.0), math.nextafter(1.0, 0.0)),
        (math.nextafter(-1.0, 0.0), math.nextafter(-1.0, 0.0)),
        (math.nextafter(1.0, math.inf), 1.0),
        (math.nextafter(-1.0, -math.inf), -1.0),
        (1e308, 1.0),
        (-1e308, -1.0),
        (np.float32(0.5), 0.5),
        (np.int64(2), 1.0),
        (True, 1.0),
        (False, 0.0),
        (Decimal("0.25"), 0.25),
        (Fraction(-1, 4), -0.25),
        ("0.125", 0.125),
    ],
)
def test_latest_signal_finite_legacy_conversions_and_signed_clipping_stay_exact(
    value: object, expected: float
) -> None:
    with patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)):
        actual = sizing.latest_signal(_position(), _frame())
    assert struct.pack("!d", actual) == struct.pack("!d", expected)


@settings(max_examples=80, deadline=None)
@given(st.floats(allow_nan=False, allow_infinity=False, width=64))
def test_latest_signal_finite_weights_preserve_conviction_and_bound_exposure(value: float) -> None:
    with patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)):
        actual = sizing.latest_signal(_position(), _frame())
    assert math.isfinite(actual) and -1.0 <= actual <= 1.0
    assert math.copysign(1.0, actual) == math.copysign(1.0, value)
    if abs(value) <= 1.0:
        assert struct.pack("!d", actual) == struct.pack("!d", value)
    else:
        assert abs(actual) == 1.0


@pytest.mark.parametrize("value", [None, complex(1.0, 2.0), object()])
def test_latest_signal_native_float_conversion_type_errors_remain(value: object) -> None:
    with (
        patch.object(sizing, "build_strategy_from_dict", return_value=_Output(value)),
        pytest.raises(TypeError),
    ):
        sizing.latest_signal(_position(), _frame())
