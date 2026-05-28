import pandas as pd
from tests.fixtures.synthetic import builders

from app.research.frames import bars_to_frame


def test_bars_to_frame_has_close_column_and_utc_index() -> None:
    frame = bars_to_frame(builders.clean_series(n=10))
    assert list(frame.columns) >= ["close"]
    assert len(frame) == 10
    assert isinstance(frame.index, pd.DatetimeIndex)
    assert str(frame.index.tz) == "UTC"
    assert frame["close"].dtype == "float64"


def test_bars_to_frame_is_sorted_by_timestamp() -> None:
    frame = bars_to_frame(list(reversed(builders.clean_series(n=10))))
    assert frame.index.is_monotonic_increasing


def test_bars_to_frame_empty_returns_empty_frame() -> None:
    frame = bars_to_frame([])
    assert len(frame) == 0
    assert "close" in frame.columns
