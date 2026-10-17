"""ADR-311: horizon CLI source identities survive equal option-value text."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from scripts import horizon_power_calibration as driver


@pytest.mark.parametrize(
    "argv,count,seed,bars,half_life,share,out",
    [
        ([], 50, 0, driver.CALIBRATION_N_BARS, 3.0, 0.409, None),
        (["3"], 3, 0, driver.CALIBRATION_N_BARS, 3.0, 0.409, None),
        (["2", "9", "--n-bars", "7400"], 2, 9, 7400, 3.0, 0.409, None),
        (["2", "7400", "--n-bars", "7400"], 2, 7400, 7400, 3.0, 0.409, None),
        (["2", "9", "--n-bars", "2"], 2, 9, 2, 3.0, 0.409, None),
        (["--n-bars", "7400", "2", "7400"], 2, 7400, 7400, 3.0, 0.409, None),
        (["2", "--n-bars", "7400", "7400"], 2, 7400, 7400, 3.0, 0.409, None),
        (["2", "9", "--half-life", "2"], 2, 9, driver.CALIBRATION_N_BARS, 2.0, 0.409, None),
        (["1", "9", "--deviation-share", "1"], 1, 9, driver.CALIBRATION_N_BARS, 3.0, 1.0, None),
        (["2", "9", "--out", "2"], 2, 9, driver.CALIBRATION_N_BARS, 3.0, 0.409, "2"),
        (["2", "9", "--out", "9"], 2, 9, driver.CALIBRATION_N_BARS, 3.0, 0.409, "9"),
        (
            ["--n-bars", "7400", "--n-bars", "2", "2", "9"],
            2,
            9,
            7400,
            3.0,
            0.409,
            None,
        ),
        (
            ["--out", "2", "--out", "9", "3", "10"],
            3,
            10,
            driver.CALIBRATION_N_BARS,
            3.0,
            0.409,
            "2",
        ),
        (
            ["2", "9", "--half-life", "", "--deviation-share", "", "--n-bars", ""],
            2,
            9,
            driver.CALIBRATION_N_BARS,
            3.0,
            0.409,
            None,
        ),
        (
            [
                "--half-life",
                "3",
                "--half-life",
                "2",
                "--deviation-share",
                "0.25",
                "--deviation-share",
                "1",
                "2",
                "9",
            ],
            2,
            9,
            driver.CALIBRATION_N_BARS,
            3.0,
            0.25,
            None,
        ),
    ],
)
def test_horizon_main_preserves_requested_identity_and_exact_scientific_calls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    argv: list[str],
    count: int,
    seed: int,
    bars: int,
    half_life: float,
    share: float,
    out: str | None,
) -> None:
    plants: list[SimpleNamespace] = []

    def plant(*args: object, **kwargs: object) -> SimpleNamespace:
        result = SimpleNamespace(
            frame=object(), conditional_mean=object(), achievable_conditional_mean=object()
        )
        plants.append(result)
        return result

    generate, scorer = Mock(side_effect=plant), Mock(return_value=1.25)
    dump = Mock(return_value='{"mock": true}')
    result = SimpleNamespace(model_dump_json=dump)
    measure, report = Mock(return_value=result), Mock()
    monkeypatch.setattr(driver, "mean_reverting_edge", generate)
    monkeypatch.setattr(driver, "oracle_sharpe_of", scorer)
    monkeypatch.setattr(driver, "measure_power", measure)
    monkeypatch.setattr(driver, "_report", report)
    monkeypatch.setattr("sys.argv", ["horizon_power_calibration.py", *argv])
    monkeypatch.chdir(tmp_path)
    driver.main()

    assert generate.call_args_list == [
        call(bars, seed=seed + i, half_life=half_life, deviation_share=share) for i in range(count)
    ]
    assert scorer.call_args_list == (
        [call(p.frame, p.conditional_mean) for p in plants]
        + [call(p.frame, p.conditional_mean, cost_rate=driver.DEFAULT_COST_RATE) for p in plants]
        + [
            call(p.frame, p.achievable_conditional_mean, cost_rate=driver.DEFAULT_COST_RATE)
            for p in plants
        ]
    )
    frames = {f"BAND{i:04d}": p.frame for i, p in enumerate(plants)}
    scores = dict.fromkeys(frames, 1.25)
    measure.assert_called_once_with(
        frames,
        [entry.name for entry in driver.STRATEGY_CATALOG],
        oracle_sharpes=scores,
        net_oracle_sharpes=scores,
        achievable_oracle_sharpes=scores,
        edge="band_reversion",
        half_life=half_life,
        deviation_share=share,
    )
    report.assert_called_once_with(result)
    if out:
        dump.assert_called_once_with(indent=2)
        assert (tmp_path / out).read_text() == '{"mock": true}\n'
        assert sorted(p.name for p in tmp_path.iterdir()) == [out]
    else:
        dump.assert_not_called()
        assert not list(tmp_path.iterdir())
