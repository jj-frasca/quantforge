"""ADR-307: option-value text cannot erase positional source count/seed identity."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from scripts import power_calibration as driver


def _mock_main(monkeypatch: pytest.MonkeyPatch, argv: list[str]) -> tuple[Mock, Mock, Mock, Mock]:
    generator = Mock(side_effect=lambda *args, **kwargs: object())
    dump = Mock(return_value='{"mock": true}')
    result = SimpleNamespace(model_dump_json=dump)
    measure = Mock(return_value=result)
    report = Mock()
    monkeypatch.setattr(driver, "autocorrelated_edge", generator)
    monkeypatch.setattr(driver, "measure_power", measure)
    monkeypatch.setattr(driver, "_report", report)
    monkeypatch.setattr("sys.argv", ["power_calibration.py", *argv])
    driver.main()
    report.assert_called_once_with(result)
    return generator, measure, report, dump


@pytest.mark.parametrize(
    "argv,n_symbols,seed,n_bars,phi,shard,n_shards,select_by",
    [
        (["2", "7400", "--n-bars", "7400"], 2, 7400, 7400, -0.2, 0, 1, "observed"),
        (["7400", "2", "--n-bars", "7400"], 7400, 2, 7400, -0.2, 0, 1, "observed"),
        (["2", "9", "--n-bars", "7400"], 2, 9, 7400, -0.2, 0, 1, "observed"),
        (["--n-bars", "7400", "2", "7400"], 2, 7400, 7400, -0.2, 0, 1, "observed"),
        (["2", "--n-bars", "7400", "7400"], 2, 7400, 7400, -0.2, 0, 1, "observed"),
        ([], 50, 0, driver.CALIBRATION_N_BARS, -0.2, 0, 1, "observed"),
        (["3"], 3, 0, driver.CALIBRATION_N_BARS, -0.2, 0, 1, "observed"),
        (
            ["--phi", "0.3", "4", "10", "--shard", "1/2", "--select-by", "walk_forward"],
            4,
            10,
            driver.CALIBRATION_N_BARS,
            0.3,
            1,
            2,
            "walk_forward",
        ),
        (
            [
                "--n-bars",
                "7400",
                "3",
                "10",
                "--n-bars",
                "42",
                "--phi",
                "0.1",
                "--phi",
                "0.2",
                "--select-by",
                "walk_forward",
                "--select-by",
                "observed",
                "--shard",
                "1/2",
                "--shard",
                "0/1",
            ],
            3,
            10,
            7400,
            0.1,
            1,
            2,
            "walk_forward",
        ),
    ],
)
def test_main_preserves_exact_requested_source_count_seed_and_option_order(
    monkeypatch: pytest.MonkeyPatch,
    argv: list[str],
    n_symbols: int,
    seed: int,
    n_bars: int,
    phi: float,
    shard: int,
    n_shards: int,
    select_by: str,
) -> None:
    generator, measure, _, dump = _mock_main(monkeypatch, argv)
    indices = [i for i in range(n_symbols) if i % n_shards == shard]
    assert generator.call_args_list == [call(n_bars, seed=seed + i, phi=phi) for i in indices]
    measure.assert_called_once()
    frames, strategies = measure.call_args.args
    assert list(frames) == [f"EDGE{i:04d}" for i in indices]
    assert len({id(value) for value in frames.values()}) == len(indices)
    assert strategies == [entry.name for entry in driver.STRATEGY_CATALOG]
    assert measure.call_args.kwargs == {"phi": phi, "select_by": select_by}
    dump.assert_not_called()


@pytest.mark.parametrize("out", ["2", "9"])
def test_numeric_relative_output_path_cannot_erase_equal_count_or_seed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, out: str
) -> None:
    monkeypatch.chdir(tmp_path)
    generator, measure, _, dump = _mock_main(monkeypatch, ["2", "9", "--out", out])
    assert generator.call_args_list == [
        call(driver.CALIBRATION_N_BARS, seed=9, phi=-0.2),
        call(driver.CALIBRATION_N_BARS, seed=10, phi=-0.2),
    ]
    assert list(measure.call_args.args[0]) == ["EDGE0000", "EDGE0001"]
    dump.assert_called_once_with(indent=2)
    assert (tmp_path / out).read_text() == '{"mock": true}\n'


def test_repeated_output_options_use_first_path_without_positional_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    generator, measure, _, dump = _mock_main(monkeypatch, ["--out", "2", "--out", "9", "3", "10"])
    assert generator.call_args_list == [
        call(driver.CALIBRATION_N_BARS, seed=i, phi=-0.2) for i in [10, 11, 12]
    ]
    assert list(measure.call_args.args[0]) == ["EDGE0000", "EDGE0001", "EDGE0002"]
    dump.assert_called_once_with(indent=2)
    assert (tmp_path / "2").read_text() == '{"mock": true}\n'
    assert not (tmp_path / "9").exists()
