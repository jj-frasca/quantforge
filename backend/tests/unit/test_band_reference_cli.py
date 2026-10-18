"""ADR-313 opt-in wiring; every expensive scientific operation is mocked."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest
from scripts import horizon_power_calibration as driver


@pytest.fixture
def harness(monkeypatch: pytest.MonkeyPatch) -> tuple[Mock, Mock, Mock]:
    plant = SimpleNamespace(
        frame=object(),
        deviation=object(),
        conditional_mean=object(),
        achievable_conditional_mean=object(),
    )
    generate = Mock(return_value=plant)
    scorer = Mock(return_value=1.25)
    measure = Mock(return_value=object())
    monkeypatch.setattr(driver, "mean_reverting_edge", generate)
    monkeypatch.setattr(driver, "oracle_sharpe_of", scorer)
    monkeypatch.setattr(driver, "measure_power", measure)
    monkeypatch.setattr(driver, "_report", Mock())
    return generate, scorer, measure


def test_conditional_cli_forwards_recorded_law_and_existing_deviations(
    monkeypatch: pytest.MonkeyPatch, harness: tuple[Mock, Mock, Mock]
) -> None:
    generate, scorer, measure = harness
    monkeypatch.setattr(
        "sys.argv",
        [
            "horizon",
            "--drift",
            "2",
            "--total-vol",
            "2",
            "--start-price",
            "2",
            "--band-reference-method",
            "conditional_simple_mean",
            "2",
            "2",
        ],
    )
    driver.main()
    assert generate.call_args_list == [
        call(
            driver.CALIBRATION_N_BARS,
            seed=seed,
            half_life=3.0,
            deviation_share=0.409,
            drift=2.0,
            total_vol=2.0,
            start_price=2.0,
        )
        for seed in (2, 3)
    ]
    scorer.assert_not_called()
    kwargs = measure.call_args.kwargs
    assert set(kwargs) == {
        "edge",
        "half_life",
        "deviation_share",
        "band_reference",
        "band_deviations",
    }
    reference = kwargs["band_reference"]
    assert reference.method == "band_conditional_simple_mean_sign_zero_start_v1"
    assert (reference.drift, reference.total_vol, reference.start_price) == (2.0, 2.0, 2.0)
    assert kwargs["band_deviations"] == dict.fromkeys(
        ("BAND0000", "BAND0001"), generate.return_value.deviation
    )


@pytest.mark.parametrize(
    "options",
    [
        ["--band-reference-method", "wrong"],
        ["--drift", "0"],
        ["--band-reference-method", "legacy", "--total-vol", ".01"],
        ["--band-reference-method", "conditional_simple_mean"],
        [
            "--band-reference-method",
            "conditional_simple_mean",
            "--drift",
            "0",
            "--total-vol",
            ".01",
        ],
        [
            "--band-reference-method",
            "conditional_simple_mean",
            "--drift",
            "0",
            "--total-vol",
            "1e-300",
            "--start-price",
            "100",
        ],
        [
            "--band-reference-method",
            "conditional_simple_mean",
            "--drift",
            "0",
            "--total-vol",
            ".01",
            "--start-price",
            "100",
            "--half-life",
            "1e300",
        ],
    ],
)
def test_invalid_cli_refuses_before_generation(
    monkeypatch: pytest.MonkeyPatch, harness: tuple[Mock, Mock, Mock], options: list[str]
) -> None:
    monkeypatch.setattr("sys.argv", ["horizon", "1", "9", *options])
    with pytest.raises((ValueError, SystemExit)):
        driver.main()
    for operation in harness:
        operation.assert_not_called()


def test_explicit_legacy_keeps_exact_old_calls(
    monkeypatch: pytest.MonkeyPatch, harness: tuple[Mock, Mock, Mock]
) -> None:
    generate, scorer, measure = harness
    monkeypatch.setattr("sys.argv", ["horizon", "--band-reference-method", "legacy", "1", "9"])
    driver.main()
    generate.assert_called_once_with(
        driver.CALIBRATION_N_BARS, seed=9, half_life=3.0, deviation_share=0.409
    )
    assert scorer.call_count == 3
    assert set(measure.call_args.kwargs) == {
        "oracle_sharpes",
        "net_oracle_sharpes",
        "achievable_oracle_sharpes",
        "edge",
        "half_life",
        "deviation_share",
    }


@pytest.mark.parametrize(
    "flag,first,later",
    [
        ("--drift", "0", "9"),
        ("--total-vol", ".012", "9"),
        ("--start-price", "100", "9"),
        ("--band-reference-method", "conditional_simple_mean", "legacy"),
    ],
)
def test_repeated_law_flags_use_first_value_and_preserve_positional_seed(
    monkeypatch: pytest.MonkeyPatch,
    harness: tuple[Mock, Mock, Mock],
    flag: str,
    first: str,
    later: str,
) -> None:
    generate, scorer, measure = harness
    options = {
        "--drift": "0",
        "--total-vol": ".012",
        "--start-price": "100",
        "--band-reference-method": "conditional_simple_mean",
    }
    tokens = [flag, first, flag, later]
    for option, value in options.items():
        if option != flag:
            tokens.extend((option, value))
    monkeypatch.setattr("sys.argv", ["horizon", *tokens, "1", "9"])
    driver.main()
    assert generate.call_count == 1
    assert generate.call_args.kwargs["seed"] == 9
    scorer.assert_not_called()
    assert measure.call_args.kwargs["band_reference"].drift == 0.0
