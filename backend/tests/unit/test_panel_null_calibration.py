"""Whole-panel artifact identity, joint-row generation, and consolidation for ADR-081."""

from datetime import date

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from app.research.lab.panel_null import (
    PanelNullCalibration,
    PanelNullCohort,
    PanelNullError,
    PanelNullReplicate,
    PanelNullShard,
    PanelSymbolExcess,
    joint_iid_panel_null,
    merge_panel_null_shards,
    panel_seed,
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
