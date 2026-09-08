"""Whole-panel artifact identity, joint-row generation, and consolidation for ADR-081."""

from dataclasses import replace
from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.research.lab.panel_null import (
    PanelDiagnosticInference,
    PanelNullCalibration,
    PanelNullCohort,
    PanelNullError,
    PanelNullReplicate,
    PanelNullShard,
    PanelSymbolExcess,
    infer_panel_null,
    joint_iid_panel_null,
    merge_panel_null_shards,
    panel_seed,
    prepare_panel_null_source,
)


def _cohort(
    *,
    source_digest: str = "a" * 64,
    n_replicates: int = 4,
    min_successful_symbols: int = 2,
) -> PanelNullCohort:
    return PanelNullCohort(
        symbols=("AAA", "BBB"),
        symbol_excesses=(
            PanelSymbolExcess(symbol="AAA", walk_forward=-0.2, purged_cv=0.1),
            PanelSymbolExcess(symbol="BBB", walk_forward=0.0, purged_cv=None),
        ),
        source_start=date(1995, 1, 3),
        source_end=date(2026, 8, 31),
        source_sha256=source_digest,
        target_n_bars=7400,
        history_tolerance=0.10,
        search_config_version="search-v1",
        gate_config_version="gate-v1",
        generator_version="joint-iid-calendar-v1",
        diagnostic_version="equal-symbol-excess-v1",
        base_seed=17,
        n_replicates=n_replicates,
        min_successful_symbols=min_successful_symbols,
    )


def _replicate(index: int, *, successful_symbols: int = 2) -> PanelNullReplicate:
    return PanelNullReplicate(
        panel_index=index,
        panel_id=f"panel-{index:03d}",
        seed=panel_seed(17, index),
        successful_symbols=successful_symbols,
        errors=(),
        walk_forward_excess=-0.01 + index / 1000,
        purged_cv_excess=index / 2000,
    )


def _calibration_with_walk_forward(values: list[float]) -> PanelNullCalibration:
    cohort = _cohort(n_replicates=len(values))
    cohort = cohort.model_copy(
        update={
            "symbol_excesses": tuple(
                value.model_copy(update={"purged_cv": value.walk_forward})
                for value in cohort.symbol_excesses
            )
        }
    )
    replicates = tuple(
        _replicate(index).model_copy(update={"walk_forward_excess": value})
        for index, value in enumerate(values)
    )
    return PanelNullCalibration(cohort=cohort, replicates=replicates)


def test_panel_null_inference_uses_fixed_tail_counts_and_plus_one_p_value() -> None:
    calibration = _calibration_with_walk_forward([-1.0] * 3 + [1.0] * 397)

    result = infer_panel_null(calibration).walk_forward

    assert isinstance(result, PanelDiagnosticInference)
    assert result.real_statistic == pytest.approx(-0.1)
    assert result.null_median == pytest.approx(1.0)
    assert result.null_p025 == pytest.approx(1.0)
    assert result.null_p975 == pytest.approx(1.0)
    assert result.lower_tail_count == 3
    assert result.upper_tail_count == 397
    assert result.two_sided_p_value == pytest.approx(8 / 401)
    assert result.tail_interval_confidence == pytest.approx(0.975)
    assert result.simultaneous_confidence == pytest.approx(0.95)
    assert result.lower_tail_interval.low == pytest.approx(0.0011875146623632955)
    assert result.lower_tail_interval.high == pytest.approx(0.024143766938848475)
    assert result.resolution == "separated_below"


def test_panel_null_inference_keeps_four_tail_hits_unresolved() -> None:
    result = infer_panel_null(_calibration_with_walk_forward([-1.0] * 4 + [1.0] * 396)).walk_forward

    assert result.lower_tail_interval.high == pytest.approx(0.02794221048906605)
    assert result.resolution == "unresolved"


def test_panel_null_inference_resolves_the_fixed_upper_tail() -> None:
    result = infer_panel_null(_calibration_with_walk_forward([-1.0] * 397 + [1.0] * 3)).walk_forward

    assert result.upper_tail_count == 3
    assert result.upper_tail_interval.high < 0.025
    assert result.resolution == "separated_above"


def test_panel_null_inference_calls_both_well_inside_tails_not_separated() -> None:
    result = infer_panel_null(
        _calibration_with_walk_forward([-1.0] * 200 + [1.0] * 200)
    ).walk_forward

    assert result.lower_tail_interval.low > 0.025
    assert result.upper_tail_interval.low > 0.025
    assert result.two_sided_p_value == 1.0
    assert result.resolution == "not_separated"


def test_panel_null_inference_does_not_filter_partial_secondary_diagnostics() -> None:
    calibration = _calibration_with_walk_forward([-1.0, 1.0, -1.0, 1.0])
    assert infer_panel_null(calibration).purged_cv is not None

    incomplete = calibration.model_copy(
        update={
            "replicates": (
                *calibration.replicates[:-1],
                calibration.replicates[-1].model_copy(update={"purged_cv_excess": None}),
            )
        }
    )
    assert infer_panel_null(incomplete).purged_cv is None

    missing_real = calibration.model_copy(update={"cohort": _cohort(n_replicates=4)})
    assert infer_panel_null(missing_real).purged_cv is None


def _source_panel() -> dict[str, pd.DataFrame]:
    index = pd.date_range("2020-01-02", periods=6, freq="B", tz="UTC")
    returns = {
        "AAA": np.array([0.0, 0.01, -0.02, 0.03, -0.01, 0.02]),
        "BBB": np.array([0.0, 0.02, -0.01, 0.04, -0.03, 0.01]),
    }
    panel: dict[str, pd.DataFrame] = {}
    for offset, (symbol, values) in enumerate(returns.items(), start=1):
        closes = 100.0 * np.cumprod(1.0 + values)
        panel[symbol] = pd.DataFrame(
            {
                "open": closes * (0.99 + offset / 1000),
                "high": closes * (1.01 + offset / 1000),
                "low": closes * (0.98 + offset / 1000),
                "close": closes,
                "volume": offset * 1000 + np.arange(len(index)),
            },
            index=index,
        )
    return panel


def test_prepare_panel_null_source_freezes_order_calendar_and_digest() -> None:
    source = _source_panel()
    source["AAA"].iloc[1, source["AAA"].columns.get_loc("volume")] = np.nan
    source["BBB"].iloc[4, source["BBB"].columns.get_loc("close")] = np.nan

    prepared = prepare_panel_null_source(source, ("BBB", "AAA"), target_n_bars=3)

    assert prepared.symbols == ("BBB", "AAA")
    assert prepared.target_n_bars == 3
    assert prepared.source_start == date(2020, 1, 6)
    assert prepared.source_end == date(2020, 1, 9)
    assert len(prepared.source_sha256) == 64
    panel = prepared.to_frames()
    assert tuple(panel) == prepared.symbols
    assert panel["AAA"].index.equals(panel["BBB"].index)
    assert panel["AAA"].index.tolist() == [
        pd.Timestamp("2020-01-06", tz="UTC"),
        pd.Timestamp("2020-01-07", tz="UTC"),
        pd.Timestamp("2020-01-09", tz="UTC"),
    ]
    assert not any(frame.isna().any().any() for frame in panel.values())


def test_prepare_panel_null_source_digest_is_canonical_and_value_sensitive() -> None:
    source = _source_panel()
    reordered = {
        symbol: frame.loc[:, ["volume", "close", "low", "high", "open"]]
        for symbol, frame in reversed(tuple(source.items()))
    }

    first = prepare_panel_null_source(source, ("AAA", "BBB"), target_n_bars=5)
    second = prepare_panel_null_source(reordered, ("AAA", "BBB"), target_n_bars=5)
    assert second.source_sha256 == first.source_sha256

    changed = {symbol: frame.copy() for symbol, frame in source.items()}
    changed["AAA"].iloc[-1, changed["AAA"].columns.get_loc("volume")] += 1
    assert (
        prepare_panel_null_source(changed, ("AAA", "BBB"), target_n_bars=5).source_sha256
        != first.source_sha256
    )
    assert (
        prepare_panel_null_source(source, ("BBB", "AAA"), target_n_bars=5).source_sha256
        != first.source_sha256
    )


def test_prepare_panel_null_source_copies_the_frozen_source() -> None:
    source = _source_panel()
    prepared = prepare_panel_null_source(source, ("AAA", "BBB"), target_n_bars=5)
    digest = prepared.source_sha256

    source["AAA"].iloc[-1, source["AAA"].columns.get_loc("close")] = 1.0
    exported = prepared.to_frames()
    exported["AAA"].iloc[-1, exported["AAA"].columns.get_loc("close")] = 2.0

    assert prepared.source_sha256 == digest
    assert prepared.to_frames()["AAA"].iloc[-1]["close"] != 2.0


def test_prepared_panel_source_direct_construction_cannot_drift_from_its_frames() -> None:
    prepared = prepare_panel_null_source(_source_panel(), ("AAA", "BBB"), target_n_bars=5)

    with pytest.raises(ValueError, match="digest"):
        replace(prepared, source_sha256="a" * 64)
    with pytest.raises(ValueError, match="calendar range"):
        replace(prepared, source_start=date(1999, 1, 1))


def test_prepare_panel_null_source_fails_closed_on_cohort_or_history_mismatch() -> None:
    source = _source_panel()
    with pytest.raises(ValueError, match=r"missing symbols.*ZZZ"):
        prepare_panel_null_source(source, ("AAA", "ZZZ"), target_n_bars=5)
    with pytest.raises(ValueError, match=r"unexpected symbols.*BBB"):
        prepare_panel_null_source(source, ("AAA",), target_n_bars=5)
    with pytest.raises(ValueError, match="duplicate symbol"):
        prepare_panel_null_source(source, ("AAA", "AAA"), target_n_bars=5)
    with pytest.raises(ValueError, match=r"complete calendar has 4 rows.*requires 5"):
        incomplete = {symbol: frame.copy() for symbol, frame in source.items()}
        incomplete["AAA"].iloc[2, incomplete["AAA"].columns.get_loc("volume")] = np.nan
        incomplete["BBB"].iloc[4, incomplete["BBB"].columns.get_loc("close")] = np.nan
        prepare_panel_null_source(incomplete, ("AAA", "BBB"), target_n_bars=5)


def test_joint_iid_panel_null_uses_one_calendar_draw_for_every_symbol() -> None:
    source = _source_panel()
    generated = joint_iid_panel_null(source, 12, seed=23)

    aaa_rows = generated["AAA"]["volume"].to_numpy(dtype=int) - 1000
    bbb_rows = generated["BBB"]["volume"].to_numpy(dtype=int) - 2000
    assert np.array_equal(aaa_rows, bbb_rows)
    assert (aaa_rows >= 1).all()  # row zero has no close-to-close return to resample

    for symbol, frame in generated.items():
        base = float(source[symbol]["close"].iloc[0])
        reconstructed = np.r_[
            float(frame["close"].iloc[0]) / base - 1.0,
            frame["close"].pct_change().iloc[1:].to_numpy(),
        ]
        expected = source[symbol]["close"].pct_change().to_numpy()[aaa_rows]
        assert reconstructed == pytest.approx(expected)


def test_joint_iid_panel_null_reconstructs_same_bar_ohlcv_geometry() -> None:
    source = _source_panel()
    first = joint_iid_panel_null(source, 10, seed=31)
    second = joint_iid_panel_null(source, 10, seed=31)

    for symbol, frame in first.items():
        pd.testing.assert_frame_equal(frame, second[symbol])
        drawn_rows = frame["volume"].to_numpy(dtype=int) - (1000 if symbol == "AAA" else 2000)
        source_rows = source[symbol].iloc[drawn_rows]
        for column in ("open", "high", "low"):
            assert (frame[column] / frame["close"]).to_numpy() == pytest.approx(
                (source_rows[column] / source_rows["close"]).to_numpy()
            )
        assert np.isfinite(frame.to_numpy()).all()
        assert (frame[["open", "high", "low", "close"]] > 0).all().all()
        assert (frame["high"] >= frame[["open", "close"]].max(axis=1)).all()
        assert (frame["low"] <= frame[["open", "close"]].min(axis=1)).all()


def test_joint_iid_panel_null_rejects_unaligned_or_incomplete_sources() -> None:
    source = _source_panel()
    misaligned = {**source, "BBB": source["BBB"].iloc[1:]}
    with pytest.raises(ValueError, match="aligned"):
        joint_iid_panel_null(misaligned, 5, seed=1)

    naive = {symbol: frame.tz_localize(None) for symbol, frame in source.items()}
    with pytest.raises(ValueError, match="timezone-aware"):
        joint_iid_panel_null(naive, 5, seed=1)

    incomplete = {symbol: frame.copy() for symbol, frame in source.items()}
    incomplete["AAA"].iloc[2, incomplete["AAA"].columns.get_loc("volume")] = np.nan
    with pytest.raises(ValueError, match="finite"):
        joint_iid_panel_null(incomplete, 5, seed=1)

    with pytest.raises(ValueError, match="at least one symbol"):
        joint_iid_panel_null({}, 5, seed=1)
    with pytest.raises(ValueError, match="n_bars"):
        joint_iid_panel_null(source, 0, seed=1)


def test_panel_cohort_requires_exactly_one_value_per_ordered_symbol() -> None:
    cohort = _cohort()
    assert cohort.symbols == ("AAA", "BBB")
    assert (cohort.base_seed, cohort.n_replicates, cohort.min_successful_symbols) == (17, 4, 2)
    assert tuple(value.symbol for value in cohort.symbol_excesses) == cohort.symbols

    payload = cohort.model_dump()
    payload["symbol_excesses"] = tuple(reversed(payload["symbol_excesses"]))
    with pytest.raises(ValidationError, match="ordered symbols"):
        PanelNullCohort.model_validate(payload)


def test_panel_cohort_rejects_duplicate_symbols_and_invalid_source_digest() -> None:
    payload = _cohort().model_dump()
    payload["symbols"] = ("AAA", "AAA")
    with pytest.raises(ValidationError, match="duplicate"):
        PanelNullCohort.model_validate(payload)

    with pytest.raises(ValidationError, match="SHA-256"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "source_sha256": "abc"})


def test_panel_artifacts_are_frozen() -> None:
    cohort = _cohort()
    with pytest.raises(ValidationError, match="frozen"):
        cohort.target_n_bars = 5400  # type: ignore[misc]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_panel_artifacts_reject_non_finite_statistics(value: float) -> None:
    with pytest.raises(ValidationError, match="finite number"):
        PanelSymbolExcess(symbol="AAA", walk_forward=value, purged_cv=0.1)
    with pytest.raises(ValidationError, match="finite number"):
        PanelSymbolExcess(symbol="AAA", walk_forward=0.1, purged_cv=value)
    with pytest.raises(ValidationError, match="finite number"):
        PanelNullReplicate(
            panel_index=0,
            panel_id="panel-000",
            seed=panel_seed(17, 0),
            successful_symbols=2,
            walk_forward_excess=value,
            purged_cv_excess=0.1,
        )
    with pytest.raises(ValidationError, match="finite number"):
        PanelNullReplicate(
            panel_index=0,
            panel_id="panel-000",
            seed=panel_seed(17, 0),
            successful_symbols=2,
            walk_forward_excess=0.1,
            purged_cv_excess=value,
        )


@pytest.mark.parametrize(
    ("replicates", "message"),
    [
        ((_replicate(0),), "complete panel indices"),
        ((_replicate(1), _replicate(0)), "ordered by panel index"),
        (
            (
                _replicate(0),
                _replicate(1).model_copy(update={"seed": panel_seed(18, 1)}),
            ),
            "derived seed",
        ),
        (
            (
                _replicate(0),
                _replicate(1).model_copy(update={"panel_id": "panel-000"}),
            ),
            "duplicate panel id",
        ),
        (
            (_replicate(0), _replicate(1, successful_symbols=1)),
            "successful-symbol floor",
        ),
    ],
)
def test_direct_calibration_construction_cannot_bypass_merge_invariants(
    replicates: tuple[PanelNullReplicate, ...], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        PanelNullCalibration(cohort=_cohort(n_replicates=2), replicates=replicates)


def test_merge_sorts_complete_panel_units_by_global_index() -> None:
    merged = merge_panel_null_shards(
        (
            PanelNullShard(cohort=_cohort(), replicates=(_replicate(2), _replicate(0))),
            PanelNullShard(cohort=_cohort(), replicates=(_replicate(3), _replicate(1))),
        ),
    )

    assert tuple(rep.panel_index for rep in merged.replicates) == (0, 1, 2, 3)
    assert merged.cohort == _cohort()


def test_panel_seed_depends_only_on_base_seed_and_global_index() -> None:
    assert panel_seed(17, 2) == panel_seed(17, 2)
    assert len({panel_seed(17, index) for index in range(4)}) == 4
    assert panel_seed(18, 2) != panel_seed(17, 2)

    wrong_seed = _replicate(0).model_copy(update={"seed": panel_seed(18, 0)})
    with pytest.raises(ValueError, match="derived seed"):
        merge_panel_null_shards(
            (PanelNullShard(cohort=_cohort(n_replicates=1), replicates=(wrong_seed,)),)
        )


@pytest.mark.parametrize(
    ("replicates", "message"),
    [
        ((_replicate(0), _replicate(0)), "duplicate panel index"),
        ((_replicate(0), _replicate(2)), "complete panel indices"),
    ],
)
def test_merge_rejects_duplicate_or_missing_panel_indices(
    replicates: tuple[PanelNullReplicate, ...], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        merge_panel_null_shards(
            (PanelNullShard(cohort=_cohort(n_replicates=2), replicates=replicates),),
        )


def test_merge_rejects_identity_drift_between_shards() -> None:
    with pytest.raises(ValueError, match="cohort identity"):
        merge_panel_null_shards(
            (
                PanelNullShard(cohort=_cohort(), replicates=(_replicate(0),)),
                PanelNullShard(cohort=_cohort(source_digest="b" * 64), replicates=(_replicate(1),)),
            ),
        )


def test_merge_rejects_partial_panels_and_duplicate_panel_ids() -> None:
    with pytest.raises(ValueError, match="successful-symbol floor"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1),
                    replicates=(_replicate(0, successful_symbols=1),),
                ),
            ),
        )


def test_merge_requires_each_replicate_to_account_for_the_frozen_cohort() -> None:
    missing_without_error = _replicate(0, successful_symbols=1)
    with pytest.raises(ValueError, match="account for every cohort symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(missing_without_error,),
                ),
            ),
        )

    unknown_error = missing_without_error.model_copy(
        update={"errors": (PanelNullError(symbol="ZZZ", message="unsearchable"),)}
    )
    with pytest.raises(ValueError, match="error symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(unknown_error,),
                ),
            ),
        )

    duplicate_errors = missing_without_error.model_copy(
        update={
            "successful_symbols": 0,
            "errors": (
                PanelNullError(symbol="AAA", message="first"),
                PanelNullError(symbol="AAA", message="second"),
            ),
        }
    )
    with pytest.raises(ValueError, match="duplicate error symbol"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=1, min_successful_symbols=1),
                    replicates=(duplicate_errors,),
                ),
            ),
        )

    duplicate_id = _replicate(1).model_copy(update={"panel_id": "panel-000"})
    with pytest.raises(ValueError, match="duplicate panel id"):
        merge_panel_null_shards(
            (
                PanelNullShard(
                    cohort=_cohort(n_replicates=2),
                    replicates=(_replicate(0), duplicate_id),
                ),
            ),
        )


def test_merge_rejects_empty_shards_and_non_positive_contracts() -> None:
    with pytest.raises(ValueError, match="at least one shard"):
        merge_panel_null_shards(())
    with pytest.raises(ValidationError, match="n_replicates"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "n_replicates": 0})
    with pytest.raises(ValidationError, match="min_successful_symbols"):
        PanelNullCohort.model_validate({**_cohort().model_dump(), "min_successful_symbols": 0})
