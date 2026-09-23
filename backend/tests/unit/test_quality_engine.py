"""DataQualityEngine: clean series passes (survivorship info only), empty fails, and missing-bars / price-anomaly / stale / split-jump heuristics each flag without blocking."""

from decimal import Decimal

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
