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
