"""DataQualityEngine: clean series passes (survivorship info only), empty fails, and missing-bars / price-anomaly / stale / split-jump heuristics each flag without blocking."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from tests.fixtures.synthetic import builders

from app.data.quality.engine import DataQualityEngine, QualityConfig


def _issue_checks(report: object) -> set[str]:
    return {issue.check for issue in report.issues}  # type: ignore[attr-defined]


def test_clean_series_passes_with_only_survivorship_info() -> None:
    report = DataQualityEngine().check(builders.clean_series(), "AAPL")
    assert report.passed is True
    severities = {i.severity for i in report.issues}
    assert "error" not in severities
    assert "warning" not in severities
    assert _issue_checks(report) == {"survivorship_risk"}


def test_empty_series_fails_with_insufficient_data_error() -> None:
    report = DataQualityEngine().check([], "AAPL")
    assert report.passed is False
    assert "insufficient_data" in _issue_checks(report)


def test_series_symbol_mismatch_fails_before_time_series_checks() -> None:
    report = DataQualityEngine().check(builders.clean_series(symbol="AAPL"), "MSFT")

    assert report.symbol == "MSFT"
    assert report.passed is False
    assert _issue_checks(report) == {"symbol_mismatch"}


def test_mixed_symbol_series_fails_before_pairwise_checks() -> None:
    series = builders.clean_series(symbol="AAPL")
    series[1] = builders.clean_series(symbol="MSFT", n=2)[1]

    report = DataQualityEngine().check(series, "AAPL")

    assert report.passed is False
    assert _issue_checks(report) == {"symbol_mismatch"}
    assert report.issues[0].context == {
        "requested_symbol": "AAPL",
        "bar_symbols": ["AAPL", "MSFT"],
    }


def test_duplicate_timestamp_fails_before_pairwise_checks() -> None:
    series = builders.clean_series(symbol="AAPL")
    series[1] = series[1].model_copy(update={"timestamp_utc": series[0].timestamp_utc})

    report = DataQualityEngine().check(series, "AAPL")

    assert report.passed is False
    assert _issue_checks(report) == {"duplicate_timestamp"}
    assert report.issues[0].context == {
        "timestamps": [series[0].timestamp_utc.isoformat()],
    }


def test_mixed_source_series_fails_before_pairwise_checks() -> None:
    series = builders.clean_series(symbol="AAPL")
    series[1] = series[1].model_copy(update={"source": "alpaca"})

    report = DataQualityEngine().check(series, "AAPL")

    assert report.passed is False
    assert _issue_checks(report) == {"source_mismatch"}
    assert report.issues[0].context == {
        "expected_source": None,
        "bar_sources": ["alpaca", "yfinance"],
    }


def test_homogeneous_source_must_match_expected_adapter_source() -> None:
    report = DataQualityEngine().check(
        builders.clean_series(symbol="AAPL"), "AAPL", expected_source="alpaca"
    )

    assert report.passed is False
    assert _issue_checks(report) == {"source_mismatch"}
    assert report.issues[0].context == {
        "expected_source": "alpaca",
        "bar_sources": ["yfinance"],
    }


def test_out_of_range_timestamps_fail_before_pairwise_checks() -> None:
    start = datetime(2024, 1, 2, tzinfo=UTC)
    end = datetime(2024, 3, 1, tzinfo=UTC)
    series = builders.clean_series(symbol="AAPL")
    series[0] = series[0].model_copy(update={"timestamp_utc": datetime(2024, 1, 1, tzinfo=UTC)})
    series[-1] = series[-1].model_copy(update={"timestamp_utc": end})

    report = DataQualityEngine().check(series, "AAPL", expected_start=start, expected_end=end)

    assert report.passed is False
    assert _issue_checks(report) == {"range_mismatch"}
    assert report.issues[0].context == {
        "expected_start": start.isoformat(),
        "expected_end": end.isoformat(),
        "timestamps": [datetime(2024, 1, 1, tzinfo=UTC).isoformat(), end.isoformat()],
    }


def test_expected_range_bounds_must_be_supplied_together() -> None:
    with pytest.raises(ValueError, match="together"):
        DataQualityEngine().check(
            builders.clean_series(symbol="AAPL"),
            "AAPL",
            expected_start=datetime(2024, 1, 1, tzinfo=UTC),
        )


def test_missing_bars_are_flagged_as_warning_without_failing() -> None:
    series = builders.with_missing_bars(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    assert "missing_bars" in _issue_checks(report)
    assert report.passed is True  # a heuristic warning does not block the gate


def test_extreme_move_is_flagged_as_price_anomaly() -> None:
    series = builders.with_extreme_move(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    assert "price_anomaly" in _issue_checks(report)


def test_stale_prices_are_flagged() -> None:
    series = builders.with_stale_prices(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    assert "stale_data" in _issue_checks(report)


def test_adj_factor_jump_is_flagged_as_split_inconsistency() -> None:
    series = builders.with_split(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    assert "split_dividend_consistency" in _issue_checks(report)


def test_unexplained_large_gap_is_flagged_as_corporate_action() -> None:
    series = builders.with_corporate_action_gap(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    assert "corporate_action" in _issue_checks(report)
    assert "price_anomaly" in _issue_checks(report)  # both independently fire


def test_moderate_anomaly_below_corporate_action_threshold_is_not_flagged() -> None:
    # -0.25 down (> 20% price_anomaly threshold) and its next-bar bounce-back
    # (0.25 / 0.75 = 33%) both stay under the 50% corporate_action threshold.
    series = builders.with_extreme_move(builders.clean_series(), pct=Decimal("-0.25"))
    report = DataQualityEngine().check(series, "AAPL")
    assert "price_anomaly" in _issue_checks(report)
    assert "corporate_action" not in _issue_checks(report)


def test_adjusted_gap_with_adj_factor_jump_flags_both_independent_checks() -> None:
    # Canonical close is already adjusted, so an adj_factor jump cannot explain away a
    # large move that remains in close. Both independent observations must be retained.
    series = builders.with_split(
        builders.with_corporate_action_gap(builders.clean_series()), factor=Decimal("0.25")
    )
    report = DataQualityEngine().check(series, "AAPL")
    assert "split_dividend_consistency" in _issue_checks(report)
    assert "corporate_action" in _issue_checks(report)


def test_stale_prices_at_end_of_series_are_flagged() -> None:
    # stale run extending to the final bar (exercises the end-of-loop flush)
    series = builders.with_stale_prices(builders.clean_series(), start_index=25, length=5)
    report = DataQualityEngine().check(series, "AAPL")
    assert "stale_data" in _issue_checks(report)


def test_survivorship_flag_can_be_disabled() -> None:
    config = QualityConfig(flag_survivorship=False)
    report = DataQualityEngine(config).check(builders.clean_series(), "AAPL")
    assert "survivorship_risk" not in _issue_checks(report)


def test_issue_messages_use_honest_wording() -> None:
    series = builders.with_extreme_move(builders.clean_series())
    report = DataQualityEngine().check(series, "AAPL")
    for issue in report.issues:
        assert "guarantee" not in issue.message.lower()
        assert "prevent" not in issue.message.lower()
