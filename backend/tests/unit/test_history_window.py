import re
from datetime import UTC, datetime
from pathlib import Path

from app.research.lab.history import (
    CALIBRATION_N_BARS,
    PRE_ADR063_SEARCH_START,
    RECENT_HISTORY_START,
    SEARCH_HISTORY_START,
)

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"

# The drivers that fetch real bars to search over. The power calibrations synthesize their own
# series and so carry the length, not the window; `test_the_calibration_drivers_share_one_length`
# covers them.
SEARCH_SIDE = {
    "shard_hunt.py",
    "hunt.py",
    "run_hunt.py",
    "null_calibration.py",
}
RECENT_SIDE = {
    "paper.py",
    "paper_broker.py",
    "consolidate_pool.py",
    "cross_sectional_hunt.py",
    "cross_sectional_forward.py",
}


def _approx_trading_days(start: datetime, end: datetime) -> int:
    return int((end - start).days * 252 / 365.25)


def test_the_search_window_starts_in_1990() -> None:
    assert datetime(1990, 1, 1, tzinfo=UTC) == SEARCH_HISTORY_START


def test_the_search_window_reaches_further_back_than_the_recent_one() -> None:
    assert SEARCH_HISTORY_START < RECENT_HISTORY_START


def test_the_null_is_calibrated_on_history_only_the_search_window_can_supply() -> None:
    """ADR-051/063: a null judged on 5,400 bars describes a gate the hunt no longer runs."""
    now = datetime.now(UTC)
    assert _approx_trading_days(RECENT_HISTORY_START, now) < CALIBRATION_N_BARS
    assert _approx_trading_days(SEARCH_HISTORY_START, now) >= CALIBRATION_N_BARS


def test_no_driver_hardcodes_its_own_history_start() -> None:
    """Nine copies of this date is how it went unexamined for six ADRs (ADR-063)."""
    offenders = sorted(
        path.name
        for path in SCRIPTS.glob("*.py")
        if re.search(r"datetime\(\s*(?:19|20)\d\d\s*,", path.read_text())
    )
    assert offenders == []


def test_every_driver_names_the_window_it_needs() -> None:
    for name in sorted(SEARCH_SIDE):
        assert "SEARCH_HISTORY_START" in (SCRIPTS / name).read_text(), name
    for name in sorted(RECENT_SIDE):
        assert "RECENT_HISTORY_START" in (SCRIPTS / name).read_text(), name


def test_the_calibration_drivers_share_one_length() -> None:
    for name in ("null_calibration.py", "power_calibration.py", "horizon_power_calibration.py"):
        source = (SCRIPTS / name).read_text()
        assert "CALIBRATION_N_BARS" in source, name
        assert not re.search(r"^N_BARS = \d+", source, re.MULTILINE), name


def test_the_window_adr_063_replaced_is_pinned_where_the_experiment_can_find_it() -> None:
    """ADR-074 measures the OLD setting, so the old setting has to be a named fact rather than a
    literal in one driver — and it must not drift when the live window does."""
    assert datetime(2005, 1, 1, tzinfo=UTC) == PRE_ADR063_SEARCH_START
    assert SEARCH_HISTORY_START < PRE_ADR063_SEARCH_START
    assert "PRE_ADR063_SEARCH_START" in (SCRIPTS / "window_experiment.py").read_text()
