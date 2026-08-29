"""How much price history each side of the platform asks the vendor for (ADR-063).

Two windows, because the platform has exactly two needs. Keeping both here — next to each other —
is the point: the length the search sees and the length the null is calibrated at MUST agree
(ADR-051), and for six ADRs they were nine independent copies of one date literal in `scripts/`.
"""

from datetime import UTC, datetime

# The single-name search window. The sealed holdout is the calendar-latest 20% of it (ADR-015), so
# this constant sets `T` in ADR-043's frontier: an edge must be a true Sharpe of 2.13 to be found
# 80% of the time over a 4.3y holdout and 1.82 over 5.9y. Both terms of that frontier fall as
# 1/sqrt(T) and only as sqrt(ln N) in universe size, which is why history is the lever (ADR-063).
SEARCH_HISTORY_START = datetime(1990, 1, 1, tzinfo=UTC)

# Everything that only needs a recent tail: the paper book, the broker, cross-sectional forward
# scoring, consolidation's position management, and the cross-sectional hunt (whose panel is bounded
# by its newest member, so older bars per symbol buy it nothing).
RECENT_HISTORY_START = datetime(2005, 1, 1, tzinfo=UTC)

# Bars of synthetic history per null/planted-edge symbol. A calibration is only informative at the
# length the hunt actually searches (ADR-051), and this is the measured MEDIAN of the discovery
# universe under SEARCH_HISTORY_START — not the maximum, because most of the universe is younger
# than the window. Fixed rather than computed from today's date so an artifact is reproducible;
# bump it deliberately as history accumulates, and both drivers' `--n-bars` overrides it.
CALIBRATION_N_BARS = 7400
