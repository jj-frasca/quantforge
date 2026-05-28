import pytest

from app.validation.report import ValidationReport


def _report(**overrides: object) -> ValidationReport:
    base: dict[str, object] = {
        "strategy_name": "sma_crossover",
        "observed_sharpe": 1.2,
        "deflated_sharpe": 0.4,
        "pbo": 0.2,
        "n_walk_forward_splits": 5,
        "n_purged_folds": 5,
    }
    base.update(overrides)
    return ValidationReport(**base)  # type: ignore[arg-type]


def test_report_passes_when_low_pbo_and_positive_deflated_sharpe() -> None:
    assert _report().passed is True


def test_report_fails_on_high_pbo() -> None:
    assert _report(pbo=0.7).passed is False


def test_report_fails_on_non_positive_deflated_sharpe() -> None:
    assert _report(deflated_sharpe=-0.1).passed is False


def test_report_rejects_pbo_out_of_unit_interval() -> None:
    with pytest.raises(ValueError, match="pbo"):
        _report(pbo=1.5)


def test_report_round_trips_json() -> None:
    report = _report(flags=["low sample size"])
    assert ValidationReport.model_validate_json(report.model_dump_json()) == report
