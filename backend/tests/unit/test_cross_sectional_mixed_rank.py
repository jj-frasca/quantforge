"""Mixed native numeric promotion must retain represented order (ADR-262)."""

from decimal import Decimal
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.engine import portfolio_returns
from app.research.cross_sectional.panel import long_short_weights


def _exact(value: object) -> Fraction:
    if isinstance(value, (int, np.integer)):
        return Fraction(int(value))
    return Fraction(float(value))


def _oracle(signals: pd.DataFrame, quantile: float) -> pd.DataFrame:
    expected = np.zeros(signals.shape)
    for row in range(len(signals)):
        valid = [col for col in range(signals.shape[1]) if not pd.isna(signals.iat[row, col])]
        if len(valid) < 2:
            continue
        ordered = sorted(valid, key=lambda col: _exact(signals.iat[row, col]))
        size = max(1, int(quantile * len(valid)))
        expected[row, ordered[:size]] = -1 / size
        expected[row, ordered[-size:]] = 1 / size
    return pd.DataFrame(expected, index=signals.index, columns=signals.columns)


def _pair(case: str) -> pd.DataFrame:
    if case == "int_float":
        return pd.DataFrame(
            {"A": np.array([2**53 + 1], dtype="int64"), "B": np.array([2**53], dtype="float64")}
        )
    if case == "uint_float":
        return pd.DataFrame(
            {"A": np.array([2**63 + 1], dtype="uint64"), "B": np.array([2**63], dtype="float64")}
        )
    if case == "uint_int":
        return pd.DataFrame(
            {"A": np.array([2**63], dtype="uint64"), "B": np.array([2**63 - 1], dtype="int64")}
        )
    if case == "int_uint":
        return pd.DataFrame(
            {"A": np.array([2**63 - 1], dtype="int64"), "B": np.array([2**63 - 2], dtype="uint64")}
        )
    return pd.DataFrame(
        {"A": np.array([2**64], dtype="float64"), "B": np.array([2**64 - 1], dtype="uint64")}
    )


@pytest.mark.parametrize("case", ["int_float", "uint_float", "uint_int", "int_uint", "float_uint"])
@pytest.mark.parametrize("reverse", [False, True])
def test_long_short_weights_preserves_mixed_native_exact_order(case: str, reverse: bool) -> None:
    signals = _pair(case)
    assert _exact(signals.iat[0, 0]) > _exact(signals.iat[0, 1])
    if reverse:
        signals = signals[["B", "A"]]
    before = signals.copy(deep=True)
    state = np.geterr()
    with np.errstate(all="raise"):
        pd.testing.assert_frame_equal(
            long_short_weights(signals, 0.5), _oracle(signals, 0.5), check_exact=True
        )
    pd.testing.assert_frame_equal(signals, before, check_exact=True)
    assert np.geterr() == state


@pytest.mark.parametrize("reverse", [False, True])
def test_long_short_weights_preserves_mixed_native_true_ties_and_missingness(reverse: bool) -> None:
    signals = pd.DataFrame(
        {
            "A": np.array([2**53, 2**53, 2**53], dtype="int64"),
            "B": [float(2**53), np.nan, float(2**53 + 2)],
            "C": np.array([2**53, 2**53, 2**53 - 1], dtype="uint64"),
        }
    )
    if reverse:
        signals = signals.loc[:, ::-1]
    for quantile in [0.2, 0.5]:
        pd.testing.assert_frame_equal(
            long_short_weights(signals, quantile), _oracle(signals, quantile), check_exact=True
        )


@pytest.mark.parametrize(
    "kind", ["int64", "uint64", "Int64", "UInt64", "bool", "fraction", "decimal"]
)
def test_long_short_weights_preserves_homogeneous_and_object_integer_inputs(kind: str) -> None:
    if kind == "bool":
        signals = pd.DataFrame({"A": [True], "B": [False]})
    elif kind in ["fraction", "decimal"]:
        scalar = Fraction if kind == "fraction" else Decimal
        signals = pd.DataFrame({"A": [scalar(2**63 + 1)], "B": [scalar(2**63)]})
    else:
        signals = pd.DataFrame({"A": [2**53 + 1], "B": [2**53]}).astype(kind)
    pd.testing.assert_frame_equal(
        long_short_weights(signals, 0.5), pd.DataFrame({"A": [1.0], "B": [-1.0]}), check_exact=True
    )


@pytest.mark.parametrize(
    "kinds", [("Int64", "Float64"), ("UInt64", "Float64"), ("UInt64", "Int64")]
)
def test_long_short_weights_preserves_nullable_mixed_numeric_inputs(kinds: tuple[str, str]) -> None:
    signals = _pair("uint_int" if kinds[1] == "Int64" else "int_float")
    signals = signals.astype(dict(zip(signals.columns, kinds, strict=True)))
    signals.loc[1] = [pd.NA, pd.NA]
    pd.testing.assert_frame_equal(
        long_short_weights(signals, 0.5), _oracle(signals, 0.5), check_exact=True
    )


def test_long_short_weights_preserves_empty_mixed_native_panel() -> None:
    signals = _pair("int_float").iloc[:0]
    pd.testing.assert_frame_equal(
        long_short_weights(signals), _oracle(signals, 0.2), check_exact=True
    )


def test_portfolio_returns_uses_exact_mixed_native_order_on_next_bar() -> None:
    signals = pd.concat([_pair("int_float")] * 2, ignore_index=True)
    prices = pd.DataFrame({"A": [100.0, 110.0], "B": [100.0, 100.0]})
    np.testing.assert_allclose(
        portfolio_returns(signals, prices, quantile=0.5, cost_rate=0.001),
        [-0.002, 0.1],
        rtol=1e-14,
        atol=0,
    )


@given(
    offsets=st.lists(st.integers(-3, 3), min_size=1, max_size=8),
    unsigned=st.booleans(),
    quantile=st.sampled_from([0.2, 0.5]),
    missing=st.booleans(),
)
def test_long_short_weights_matches_exact_mixed_native_order_oracle(
    offsets: list[int], unsigned: bool, quantile: float, missing: bool
) -> None:
    base = 2**63 if unsigned else 2**53
    signals = pd.DataFrame(
        {
            "A": np.array([base + off for off in offsets], dtype="uint64" if unsigned else "int64"),
            "B": [float(base)] * len(offsets),
            "C": [float(base + 4096)] * len(offsets),
        }
    )
    if missing:
        signals.iat[0, 1] = np.nan
    pd.testing.assert_frame_equal(
        long_short_weights(signals, quantile), _oracle(signals, quantile), check_exact=True
    )


def test_long_short_weights_preserves_small_mixed_native_and_bool_scores() -> None:
    signals = pd.DataFrame(
        {
            "A": np.array([3, 1], dtype="int8"),
            "B": np.array([1, 1], dtype="uint8"),
            "C": np.array([2, np.nan], dtype="float16"),
            "D": [True, False],
        }
    )
    pd.testing.assert_frame_equal(
        long_short_weights(signals, 0.5), _oracle(signals, 0.5), check_exact=True
    )
