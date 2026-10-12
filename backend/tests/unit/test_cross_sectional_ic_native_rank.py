"""Represented IC score ordering must survive pairwise masking (ADR-264)."""

import math
from fractions import Fraction

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.cross_sectional.engine import asset_returns
from app.research.cross_sectional.ic import rank_ic


def _exact(value: object) -> Fraction:
    if isinstance(value, (int, np.integer, np.bool_)):
        return Fraction(int(value))
    numerator, denominator = value.as_integer_ratio()
    return Fraction(numerator, denominator)


def _average_ranks(values: list[Fraction]) -> list[float]:
    return [
        1
        + sum(other < value for other in values)
        + (sum(other == value for other in values) - 1) / 2
        for value in values
    ]


def _oracle(signals: pd.DataFrame, prices: pd.DataFrame) -> pd.Series:
    observations = []
    dates = []
    forward = asset_returns(prices).shift(-1)
    for row in range(len(signals)):
        valid = [
            col
            for col in range(signals.shape[1])
            if not pd.isna(signals.iat[row, col]) and not pd.isna(forward.iat[row, col])
        ]
        if len(valid) < 2:
            continue
        a = _average_ranks([_exact(signals.iat[row, col]) for col in valid])
        b = _average_ranks([_exact(forward.iat[row, col]) for col in valid])
        center = (len(valid) + 1) / 2
        a = [value - center for value in a]
        b = [value - center for value in b]
        aa = math.fsum(value * value for value in a)
        bb = math.fsum(value * value for value in b)
        if aa == 0 or bb == 0:
            continue
        observations.append(
            math.fsum(x * y for x, y in zip(a, b, strict=True)) / (math.sqrt(aa) * math.sqrt(bb))
        )
        dates.append(signals.index[row])
    return pd.Series(
        observations,
        index=signals.index[:0] if not dates else pd.Index(dates),
        name="rank_ic",
        dtype=float,
    )


def _prices() -> pd.DataFrame:
    return pd.DataFrame(
        {"A": [100.0, 120.0, 144.0], "B": [100.0, 110.0, 121.0], "C": [100.0, 100.0, 100.0]}
    )


def _signals(kind: str) -> pd.DataFrame:
    if kind in ["int64", "uint64", "Int64", "UInt64"]:
        base = 2**63 if kind in ["uint64", "UInt64"] else 2**53
        return pd.DataFrame({"A": [base + 1] * 3, "B": [base] * 3, "C": [0] * 3}).astype(kind)
    if kind == "mixed":
        return pd.DataFrame(
            {"A": np.array([2**53 + 1] * 3, dtype="int64"), "B": [float(2**53)] * 3, "C": [0.0] * 3}
        )
    if kind == "wide_large":
        scale = np.sqrt(np.longdouble(np.finfo(np.longdouble).max))
        values = [2 * scale, scale, np.longdouble(0)]
    elif kind == "wide_near":
        values = [
            np.longdouble(1) + np.finfo(np.longdouble).eps,
            np.longdouble(1),
            np.longdouble(0),
        ]
    else:
        scale = np.sqrt(np.longdouble(np.finfo(np.longdouble).max))
        values = [2 / scale, 1 / scale, np.longdouble(0)]
    return pd.DataFrame(
        np.tile(np.array(values, dtype=np.longdouble), (3, 1)), columns=["A", "B", "C"]
    )


@pytest.mark.parametrize(
    "kind", ["int64", "uint64", "mixed", "wide_large", "wide_near", "wide_small"]
)
@pytest.mark.parametrize("reverse", [False, True])
def test_rank_ic_preserves_original_native_order_before_masking(kind: str, reverse: bool) -> None:
    signals, prices = _signals(kind), _prices()
    assert _exact(signals.iat[0, 0]) > _exact(signals.iat[0, 1]) > _exact(signals.iat[0, 2])
    if reverse:
        signals, prices = signals.loc[:, ::-1], prices.loc[:, ::-1]
    before = signals.copy(deep=True), prices.copy(deep=True)
    state = np.geterr()
    with np.errstate(all="raise"):
        actual = rank_ic(signals, prices)
    pd.testing.assert_series_equal(
        actual, _oracle(signals, prices), check_exact=False, rtol=1e-14, atol=0
    )
    np.testing.assert_allclose(actual, 1.0, rtol=1e-14, atol=0)
    pd.testing.assert_frame_equal(signals, before[0], check_exact=True)
    pd.testing.assert_frame_equal(prices, before[1], check_exact=True)
    assert np.geterr() == state


def test_rank_ic_preserves_native_wide_forward_return_order() -> None:
    scale = np.sqrt(np.longdouble(np.finfo(np.longdouble).max)) / 10
    prices = pd.DataFrame(
        np.array(
            [[1.0, 1.0, 1.0], [2 * scale, scale, 1.0], [4 * scale, 2 * scale, 1.0]],
            dtype=np.longdouble,
        ),
        columns=["A", "B", "C"],
    )
    assert np.isfinite(asset_returns(prices).to_numpy()).all()
    signals = pd.DataFrame({"A": [3.0] * 3, "B": [2.0] * 3, "C": [1.0] * 3})
    with np.errstate(all="raise"):
        actual = rank_ic(signals, prices)
    pd.testing.assert_series_equal(
        actual, _oracle(signals, prices), check_exact=False, rtol=1e-14, atol=0
    )
    assert actual.iloc[0] == pytest.approx(1.0)


@pytest.mark.parametrize("kind", ["int64", "uint64", "Int64", "UInt64"])
def test_rank_ic_retains_real_average_ties_with_native_integers(kind: str) -> None:
    signals = _signals(kind)
    signals["B"] = signals["A"]
    actual = rank_ic(signals, _prices())
    pd.testing.assert_series_equal(
        actual, _oracle(signals, _prices()), check_exact=False, rtol=1e-14, atol=0
    )
    np.testing.assert_allclose(actual, math.sqrt(3) / 2, rtol=1e-14, atol=0)


@pytest.mark.parametrize(
    "kind", ["float64", "float32", "Float64", "Int64", "UInt64", "object", "bool"]
)
def test_rank_ic_preserves_ordinary_and_extension_mask_rank_paths(kind: str) -> None:
    values = [[3, 2, 1], [1, 2, 3], [2, 2, 2]] if kind != "bool" else [[True, False, False]] * 3
    signals = pd.DataFrame(values, columns=["A", "B", "C"]).astype(kind)
    pd.testing.assert_series_equal(
        rank_ic(signals, _prices()),
        _oracle(signals, _prices()),
        check_exact=False,
        rtol=1e-14,
        atol=0,
    )


def test_rank_ic_preserves_pairwise_missing_warmup_and_undefined_dates() -> None:
    signals = _signals("wide_near")
    signals.iloc[0] = np.nan
    signals.iat[1, 1] = np.nan
    actual = rank_ic(signals, _prices())
    assert actual.index.tolist() == [1]
    pd.testing.assert_series_equal(
        actual, _oracle(signals, _prices()), check_exact=False, rtol=1e-14, atol=0
    )


@pytest.mark.parametrize("empty", ["rows", "columns"])
def test_rank_ic_preserves_empty_native_panels(empty: str) -> None:
    signals, prices = _signals("int64"), _prices()
    signals = signals.iloc[:0] if empty == "rows" else signals.iloc[:, :0]
    prices = prices.iloc[:0] if empty == "rows" else prices.iloc[:, :0]
    pd.testing.assert_series_equal(
        rank_ic(signals, prices), _oracle(signals, prices), check_exact=True
    )


@given(offsets=st.lists(st.integers(-4, 4), min_size=3, max_size=8), unsigned=st.booleans())
def test_rank_ic_matches_exact_native_average_rank_oracle(
    offsets: list[int], unsigned: bool
) -> None:
    base = 2**63 if unsigned else 2**53
    values = np.array([base + value for value in offsets], dtype="uint64" if unsigned else "int64")
    signals = pd.DataFrame(np.tile(values, (3, 1)))
    growth = 1 + (np.arange(len(values)) + 1) / 100
    prices = pd.DataFrame(np.vstack([np.ones(len(values)), growth, growth * growth]))
    pd.testing.assert_series_equal(
        rank_ic(signals, prices),
        _oracle(signals, prices),
        check_exact=False,
        rtol=1e-14,
        atol=1e-15,
    )
