"""ADR-308: explicit sign-reference attribution without source draws or search."""

from fractions import Fraction
from typing import Any
from unittest.mock import Mock

import pandas as pd
import pytest
from pydantic import ValidationError
from scripts import power_calibration as driver

from app.research.backtesting.engine import DEFAULT_COST_RATE
from app.research.lab import calibration as cal
from app.research.lab.gate import GateConfig
from app.research.lab.universe import expected_max_sharpe_under_null

LEGACY = {"method": "ar1_phi_lag_sign_v1", "drift": None}
CONDITIONAL = {"method": "ar1_conditional_mean_sign_v1", "drift": 0.001}


def cell(**updates: Any) -> cal.PowerCalibration:
    return cal.PowerCalibration.model_validate(
        {
            "n_symbols": 1,
            "n_detected": 0,
            "detection_rate": 0.0,
            "n_clear_deflation_bar": 0,
            "deflation_bar": 0.0,
            "phi": -0.2,
            "oracle_sharpes": [1.0],
            "net_oracle_sharpes": [0.9],
            "holdout_years": [2.0],
            "n_bars": [1000],
            "errors": {},
            "gate_config_version": "g",
            "search_config_version": "s",
            **updates,
        }
    )


def test_reference_retains_explicit_method_and_drift() -> None:
    result = cell(ar1_reference=CONDITIONAL)
    assert result.model_dump()["ar1_reference"] == CONDITIONAL


@pytest.mark.parametrize(
    "reference",
    [
        {"method": "unknown", "drift": None},
        {"method": LEGACY["method"], "drift": 0.0},
        {"method": CONDITIONAL["method"], "drift": None},
        *(
            {"method": CONDITIONAL["method"], "drift": value}
            for value in [True, "0.1", float("inf"), float("nan"), 10**400]
        ),
        CONDITIONAL | {"extra": 1},
    ],
)
def test_reference_rejects_invalid_original_metadata(reference: Any) -> None:
    with pytest.raises(ValidationError):
        cell(ar1_reference=reference)


@pytest.mark.parametrize(
    "updates",
    [
        {"edge": "band_reversion"},
        {"phi": None},
        {"phi": 1.0},
        {"phi": -1.0},
    ],
)
def test_conditional_reference_requires_ar1_stationary_phi(updates: Any) -> None:
    with pytest.raises(ValidationError):
        cell(ar1_reference=CONDITIONAL, **updates)


def test_legacy_reference_preserves_finite_phi_domain() -> None:
    assert cell(ar1_reference=LEGACY, phi=2.0).phi == 2.0


@pytest.mark.parametrize("drift", [0, -0.001, Fraction(1, 10**12)])
def test_reference_normalizes_real_drift_and_revalidates_unchecked_copies(drift: Any) -> None:
    result = cell(ar1_reference=CONDITIONAL | {"drift": drift})
    reference = result.ar1_reference
    assert reference is not None
    assert type(reference.drift) is float
    with pytest.raises(ValidationError):
        reference.drift = 1.0  # type: ignore[misc]  # exercise frozen runtime boundary
    bad = reference.model_copy(update={"drift": True})
    with pytest.raises(ValidationError):
        cell(ar1_reference=bad)
    with pytest.raises(ValidationError):
        cal.collect_power_sweep([result.model_copy(update={"ar1_reference": bad})])


def test_collect_and_reconstruct_bind_reference_identity() -> None:
    sweep = cal.collect_power_sweep([cell(ar1_reference=CONDITIONAL)])
    assert sweep.model_dump()["ar1_reference"] == CONDITIONAL
    for other in [None, LEGACY, CONDITIONAL | {"drift": 0.002}]:
        with pytest.raises(ValueError, match="reference"):
            cal.collect_power_sweep([cell(ar1_reference=CONDITIONAL), cell(ar1_reference=other)])
        with pytest.raises(ValueError, match="reference"):
            cal.PowerSweep.model_validate(sweep.model_dump() | {"ar1_reference": other})
    with pytest.raises(ValueError):
        cal.PowerSweep.model_validate(sweep.model_dump() | {"edge": "band_reversion"})


@pytest.mark.parametrize("other", [None, LEGACY, CONDITIONAL | {"drift": 0.002}])
def test_capture_refuses_reference_changes(other: Any) -> None:
    before = cal.collect_power_sweep([cell(ar1_reference=CONDITIONAL)])
    after = cal.collect_power_sweep([cell(ar1_reference=other, search_config_version="new")])
    with pytest.raises(ValueError, match="reference"):
        cal.compare_power_sweeps(before, after)


def test_capture_preserves_historical_unknown_semantics() -> None:
    before = cal.collect_power_sweep([cell()])
    after = cal.collect_power_sweep([cell(search_config_version="new")])
    assert len(cal.compare_power_sweeps(before, after)) == 1


@pytest.mark.parametrize(
    "updates",
    [
        {"edge": "custom"},
        {"phi": None},
        {"phi": 1.0},
        {"oracle_sharpes": {"X": 1.0}},
        {"net_oracle_sharpes": {"X": 1.0}},
        {"achievable_oracle_sharpes": {"X": 1.0}},
    ],
)
def test_measure_refuses_contradictions_before_scorers_or_search(
    monkeypatch: pytest.MonkeyPatch,
    updates: Any,
) -> None:
    scorer = Mock(side_effect=AssertionError("scorer must not run"))
    monkeypatch.setattr(cal, "oracle_sharpe", scorer)
    monkeypatch.setattr(cal, "ar1_conditional_mean_sign_sharpe", scorer)
    monkeypatch.setattr(cal, "run_search", scorer)
    with pytest.raises(ValueError):
        cal.measure_power(
            {"X": pd.DataFrame()},
            [],
            **{
                "phi": -0.2,
                "ar1_reference": CONDITIONAL,
                **updates,
            },
        )
    scorer.assert_not_called()


@pytest.mark.parametrize(
    "argv",
    [
        ["2", "7400", "--ar1-reference-method", "conditional_mean", "--drift", "0.001"],
        ["2", "7400", "--drift", "0.001", "--ar1-reference-method", "conditional_mean"],
    ],
)
def test_cli_passes_same_explicit_drift_without_positional_collisions(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    generate, measure = Mock(), Mock()
    monkeypatch.setattr(driver, "autocorrelated_edge", generate)
    monkeypatch.setattr(driver, "measure_power", measure)
    monkeypatch.setattr(driver, "_report", Mock())
    monkeypatch.setattr("sys.argv", ["power_calibration.py", *argv])
    driver.main()
    assert [call.kwargs["seed"] for call in generate.call_args_list] == [7400, 7401]
    assert all(call.kwargs["drift"] == 0.001 for call in generate.call_args_list)
    assert measure.call_args.kwargs["ar1_reference"].model_dump() == CONDITIONAL


@pytest.mark.parametrize(
    "argv",
    [
        ["--ar1-reference-method", "conditional_mean"],
        ["--drift", "0.1"],
        ["--ar1-reference-method", "bad"],
        ["--ar1-reference-method", "conditional_mean", "--drift", "nan"],
    ],
)
def test_cli_refuses_invalid_reference_before_generation(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
) -> None:
    generate = Mock(side_effect=AssertionError("no generation"))
    monkeypatch.setattr(driver, "autocorrelated_edge", generate)
    monkeypatch.setattr("sys.argv", ["power_calibration.py", *argv])
    with pytest.raises((ValueError, SystemExit)):
        driver.main()
    generate.assert_not_called()


def test_ar_driver_report_names_reference_without_upper_bound_claim(
    capsys: pytest.CaptureFixture[str],
) -> None:
    driver._report(cell(ar1_reference=CONDITIONAL, finalist_observed_sharpes=[0.4]))
    report = capsys.readouterr().out
    assert "ar1_conditional_mean_sign_v1; drift=0.001" in report
    assert "CAPTURE UPPER BOUND" not in report
    assert "effect size actually planted" not in report
    assert "selected in-sample reference-relative" in report


@pytest.mark.parametrize("mode", ["conditional", "legacy", "custom", "external"])
def test_measure_dispatches_reference_and_retains_procedure(
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
) -> None:
    from types import SimpleNamespace

    from app.research.lab.gate import GateResult

    frame = pd.DataFrame({"close": [100.0] * 1000})
    search = Mock(return_value=SimpleNamespace(graduate=None, best_gate_result=None))
    monkeypatch.setattr(cal, "run_search", search)
    monkeypatch.setattr(cal, "split_holdout", lambda *_: (None, SimpleNamespace(n_bars=252)))
    monkeypatch.setattr(
        cal,
        "_finalist",
        lambda *_: SimpleNamespace(
            observed_sharpe=0.4,
            deflated_sharpe_probability=None,
            strategy_name="sma",
        ),
    )
    monkeypatch.setattr(cal, "_best_by_category", lambda *_: {})
    monkeypatch.setattr(
        cal,
        "_calibration_symbol_verdict",
        lambda *_: cal.CalibrationSymbolVerdict(
            symbol="X",
            deflated_sharpe_probability=None,
            gate_result=GateResult(
                passed=False,
                dsr_ok=False,
                pbo_ok=False,
                stability_ok=False,
                mintrl_ok=False,
                holdout_ok=False,
                beats_buy_and_hold_ok=False,
                required_track_record_years=1.0,
                gate_config_version=GateConfig().version_hash,
                holdout_sharpe=0.1,
                holdout_n_bars=252,
            ),
            holdout_sharpe=0.1,
            holdout_n_bars=252,
        ),
    )
    legacy, conditional = Mock(side_effect=[1.2, 1.1]), Mock(side_effect=[2.2, 2.1])
    monkeypatch.setattr(cal, "oracle_sharpe", legacy)
    monkeypatch.setattr(cal, "ar1_conditional_mean_sign_sharpe", conditional)
    kwargs: dict[str, Any] = {"phi": -0.2}
    expected: Any = LEGACY
    if mode == "conditional":
        kwargs["ar1_reference"] = CONDITIONAL
        expected = CONDITIONAL
    elif mode == "custom":
        kwargs["edge"] = "custom"
        expected = None
    elif mode == "external":
        kwargs = {"oracle_sharpes": {"X": 3.0}, "net_oracle_sharpes": {"X": 2.0}}
        expected = None
    result = cal.measure_power({"X": frame}, ["sma"], **kwargs)
    assert result.model_dump()["ar1_reference"] == expected
    assert result.n_detected == 0
    scorer = conditional if mode == "conditional" else legacy
    if mode != "external":
        assert scorer.call_count == 2
        assert scorer.call_args_list[0].args[0] is frame
        assert scorer.call_args_list[0].kwargs == (
            {"phi": -0.2, "drift": 0.001} if mode == "conditional" else {"phi": -0.2}
        )
        assert scorer.call_args_list[1].kwargs == (
            dict(scorer.call_args_list[0].kwargs) | {"cost_rate": DEFAULT_COST_RATE}
        )
        assert list(result.oracle_sharpes) == [2.2 if mode == "conditional" else 1.2]
        assert list(result.net_oracle_sharpes) == [2.1 if mode == "conditional" else 1.1]
    else:
        legacy.assert_not_called()
        assert result.oracle_sharpes == [3.0]
    if mode != "conditional":
        conditional.assert_not_called()
    else:
        legacy.assert_not_called()
    assert search.call_args.args[0] is frame
    assert search.call_args.args[1:] == ("X", ["sma"])
    assert search.call_args.kwargs["select_by"] == "observed"


def test_reports_preserve_band_reference_wording(capsys: pytest.CaptureFixture[str]) -> None:
    from scripts.consolidate_power_calibration import _report

    _report(cal.collect_power_sweep([cell(edge="band_reversion", phi=None, half_life=2.0)]))
    assert "AR sign reference" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "reference",
    [
        None,
        LEGACY,
        CONDITIONAL | {"drift": 0.0},
        CONDITIONAL | {"drift": -0.0001},
        CONDITIONAL | {"drift": 1e-120},
    ],
)
def test_api_preserves_reference_identity_without_changing_compatibility(
    tmp_path: Any,
    reference: Any,
) -> None:
    from fastapi.testclient import TestClient

    from app.api.v1.lab import get_power_calibration_path
    from app.main import app

    sweep = cal.collect_power_sweep([cell(ar1_reference=reference)])
    path = tmp_path / "power.json"
    original = sweep.model_dump_json()
    path.write_text(original)
    app.dependency_overrides[get_power_calibration_path] = lambda: tmp_path
    try:
        response = TestClient(app).get("/api/v1/power-calibration")
        assert response.status_code == 200
        row = response.json()[0]
        assert row["ar1_reference"] == reference
        assert row["cells"][0]["ar1_reference"] == reference
        assert row["cells"][0]["oracle_sharpes"] == [1.0]
        assert row["compatibility"]["status"] == "DIFFERENT"
        assert path.read_text() == original
    finally:
        app.dependency_overrides.pop(get_power_calibration_path, None)


@pytest.mark.parametrize("reference", [LEGACY, CONDITIONAL])
def test_detection_only_joint_comparison_unchanged_by_reference(reference: Any) -> None:
    from app.research.lab.gate import GateResult
    from app.research.lab.probability_dsr import compare_probability_dsr_gate

    def verdict(symbol: str) -> cal.CalibrationSymbolVerdict:
        return cal.CalibrationSymbolVerdict(
            symbol=symbol,
            deflated_sharpe_probability=0.1,
            gate_result=GateResult(
                passed=False,
                dsr_ok=False,
                pbo_ok=True,
                stability_ok=True,
                mintrl_ok=True,
                holdout_ok=True,
                beats_buy_and_hold_ok=True,
                required_track_record_years=1.0,
                gate_config_version="g",
                holdout_sharpe=0.1,
                holdout_n_bars=252,
            ),
            holdout_sharpe=0.1,
            holdout_n_bars=252,
        )

    nulls = []
    for mode in ["iid_normal", "bootstrap:SPY"]:
        verdicts = [verdict(f"N{i}") for i in range(200)]
        nulls.append(
            cal.NullCalibration(
                n_symbols=200,
                n_graduates=0,
                false_graduation_rate=0.0,
                n_clear_deflation_bar=0,
                deflation_bar=expected_max_sharpe_under_null(200, 1.0),
                max_deflated_sharpe=-0.1,
                max_holdout_sharpe=None,
                graduates=[],
                holdout_years=[1.0] * 200,
                n_bars=[1000] * 200,
                errors={},
                gate_config_version="g",
                search_config_version="s",
                null_mode=mode,
                symbol_diagnostics=[
                    cal.NullSymbolDiagnostics(
                        symbol=v.symbol,
                        n_bars=1000,
                        holdout_years=1.0,
                        deflated_sharpe_probability=v.deflated_sharpe_probability,
                        calibration_verdict=v,
                    )
                    for v in verdicts
                ],
            )
        )
    power_verdicts = [verdict(f"X{i}") for i in range(50)]
    cells = [
        cell(
            n_symbols=50,
            phi=phi,
            n_bars=[1000] * 50,
            holdout_years=[1.0] * 50,
            symbol_verdicts=power_verdicts,
            finalist_deflated_sharpe_probabilities=[0.1] * 50,
        )
        for phi in [-0.3, 0.3]
    ]
    unknown = cal.collect_power_sweep(cells)
    known = cal.collect_power_sweep(
        [
            cal.PowerCalibration.model_validate(c.model_dump() | {"ar1_reference": reference})
            for c in cells
        ]
    )
    assert compare_probability_dsr_gate(nulls, known) == compare_probability_dsr_gate(
        nulls, unknown
    )


@pytest.mark.parametrize(
    "reference",
    [
        {"method": "bad", "drift": None},
        CONDITIONAL | {"drift": True},
        CONDITIONAL | {"drift": 10**400},
        CONDITIONAL | {"extra": "bad"},
    ],
)
def test_measure_rejects_invalid_reference_before_any_scorer(
    monkeypatch: pytest.MonkeyPatch,
    reference: Any,
) -> None:
    forbidden = Mock(side_effect=AssertionError("no scorer/search"))
    for name in ["oracle_sharpe", "ar1_conditional_mean_sign_sharpe", "run_search"]:
        monkeypatch.setattr(cal, name, forbidden)
    with pytest.raises(ValueError):
        cal.measure_power({"X": pd.DataFrame()}, [], phi=-0.2, ar1_reference=reference)
    forbidden.assert_not_called()


def test_cli_refuses_explicit_empty_reference_method_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = Mock(side_effect=AssertionError("no source generation"))
    monkeypatch.setattr(driver, "autocorrelated_edge", generator)
    monkeypatch.setattr("sys.argv", ["power_calibration.py", "--ar1-reference-method", ""])
    with pytest.raises(SystemExit):
        driver.main()
    generator.assert_not_called()
