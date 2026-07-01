"""Graduation gate (ADR-015/016): the deterministic verdict that decides whether a searched
strategy is a 'winner'. Thresholds live in a versioned GateConfig; the MinTRL check enforces
that the track record is long enough for the Sharpe AND the trial count. Pure and tested — the
agent may rank/explain survivors but cannot override this."""

import math

import pytest

from app.research.lab.gate import GateConfig, GateResult, GraduationGate, minbtl_years
from app.research.lab.holdout import HoldoutScore
from app.validation.report import ValidationReport


def _report(dsr: float, pbo: float, stability: float, observed: float) -> ValidationReport:
    return ValidationReport(
        strategy_name="sma_crossover",
        observed_sharpe=observed,
        deflated_sharpe=dsr,
        pbo=pbo,
        parameter_stability_score=stability,
        n_walk_forward_splits=5,
        n_purged_folds=5,
    )


def _holdout(sharpe: float) -> HoldoutScore:
    return HoldoutScore(sharpe=sharpe, total_return=0.1, n_bars=252)


# ---- minbtl_years ---------------------------------------------------------------------------


def test_minbtl_matches_the_bailey_lopez_de_prado_approximation() -> None:
    # ~2 ln(N) / SR^2. N=100, SR=1 -> ~9.21 years (the number we quoted Joe).
    assert minbtl_years(100, 1.0) == pytest.approx(2 * math.log(100))


def test_minbtl_is_zero_for_a_single_trial() -> None:
    assert minbtl_years(1, 1.5) == 0.0  # ln(1) = 0: no selection penalty for one trial


def test_minbtl_is_infinite_for_a_non_positive_sharpe() -> None:
    assert minbtl_years(50, 0.0) == math.inf
    assert minbtl_years(50, -0.5) == math.inf


def test_minbtl_rejects_non_positive_trials() -> None:
    with pytest.raises(ValueError):
        minbtl_years(0, 1.0)


# ---- GateConfig -----------------------------------------------------------------------------


def test_gate_config_version_hash_is_deterministic_and_sensitive() -> None:
    a = GateConfig()
    b = GateConfig()
    assert a.version_hash == b.version_hash
    assert GateConfig(pbo_max=0.4).version_hash != a.version_hash


# ---- GraduationGate -------------------------------------------------------------------------


def test_a_strong_candidate_with_enough_history_graduates() -> None:
    result = GraduationGate().evaluate(
        report=_report(dsr=1.0, pbo=0.1, stability=0.8, observed=1.5),
        track_record_years=12.0,
        n_trials=50,
        holdout=_holdout(0.8),
        config=GateConfig(),
    )
    assert isinstance(result, GateResult)
    assert result.passed is True
    assert result.reasons == []


def test_high_pbo_fails_with_a_reason() -> None:
    result = GraduationGate().evaluate(
        report=_report(dsr=1.0, pbo=0.7, stability=0.8, observed=1.5),
        track_record_years=12.0,
        n_trials=50,
        holdout=_holdout(0.8),
        config=GateConfig(),
    )
    assert result.passed is False
    assert result.pbo_ok is False
    assert any("pbo" in r.lower() for r in result.reasons)


def test_negative_deflated_sharpe_fails() -> None:
    result = GraduationGate().evaluate(
        report=_report(dsr=-0.2, pbo=0.1, stability=0.8, observed=1.5),
        track_record_years=12.0,
        n_trials=50,
        holdout=_holdout(0.8),
        config=GateConfig(),
    )
    assert result.passed is False
    assert result.dsr_ok is False


def test_fragile_parameters_fail_stability() -> None:
    result = GraduationGate().evaluate(
        report=_report(dsr=1.0, pbo=0.1, stability=0.3, observed=1.5),
        track_record_years=12.0,
        n_trials=50,
        holdout=_holdout(0.8),
        config=GateConfig(),
    )
    assert result.passed is False
    assert result.stability_ok is False
    assert any("stability" in r.lower() for r in result.reasons)


def test_insufficient_track_record_for_the_trial_count_fails_mintrl() -> None:
    # SR=1, N=1000 -> required ~13.8y; only 5y available.
    result = GraduationGate().evaluate(
        report=_report(dsr=0.9, pbo=0.1, stability=0.8, observed=1.0),
        track_record_years=5.0,
        n_trials=1000,
        holdout=_holdout(0.8),
        config=GateConfig(),
    )
    assert result.passed is False
    assert result.mintrl_ok is False
    assert result.required_track_record_years == pytest.approx(2 * math.log(1000))


def test_holdout_that_does_not_survive_fails() -> None:
    result = GraduationGate().evaluate(
        report=_report(dsr=1.0, pbo=0.1, stability=0.8, observed=1.5),
        track_record_years=12.0,
        n_trials=50,
        holdout=_holdout(-0.3),
        config=GateConfig(),
    )
    assert result.passed is False
    assert result.holdout_ok is False
