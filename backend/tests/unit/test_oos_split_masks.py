"""Masked storage indexes are not identified split observations (ADR-248)."""

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.validation import purged_cv as pcv
from app.validation import walk_forward as wf

PERFORMANCE = np.array(
    [
        [0.01, 0.0],
        [-0.1, 0.2],
        [0.03, -0.01],
        [0.04, -0.02],
        [0.02, -0.03],
        [0.01, -0.04],
    ]
)


def evaluate(
    mode: str, train: np.ndarray, test: np.ndarray, *, benchmark: np.ndarray | None = None
) -> wf.WalkForwardResult | pcv.PurgedCVResult:
    if mode == "walk":
        return wf.walk_forward_evaluate(PERFORMANCE, [(train, test)], benchmark=benchmark)
    return pcv.purged_cv_evaluate(PERFORMANCE, [(train, test)], embargo=1, benchmark=benchmark)


@pytest.mark.parametrize("mode", ["walk", "purged"])
@pytest.mark.parametrize("side", ["train", "test"])
@pytest.mark.parametrize("mask", [[False, True], [True, True]])
def test_missing_split_identity_refuses_without_source_mutation(
    mode: str, side: str, mask: list[bool]
) -> None:
    train = np.ma.array([0, 1], mask=mask if side == "train" else False)
    test = np.ma.array([3, 4], mask=mask if side == "test" else False)
    originals = [(rows.data.copy(), np.ma.getmaskarray(rows).copy()) for rows in (train, test)]
    with pytest.raises(ValueError, match="masked"):
        evaluate(mode, train, test)
    for rows, (data, original_mask) in zip((train, test), originals, strict=True):
        np.testing.assert_array_equal(rows.data, data)
        np.testing.assert_array_equal(np.ma.getmaskarray(rows), original_mask)


@pytest.mark.parametrize("mode", ["walk", "purged"])
@pytest.mark.parametrize("side", ["train", "test"])
def test_mask_refusal_precedes_any_selection_or_scoring(
    mode: str, side: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    def unexpected_score(_: object) -> float:
        pytest.fail("missing split identity cannot reach a score")

    monkeypatch.setattr(wf if mode == "walk" else pcv, "_sharpe", unexpected_score)
    train = np.ma.array([0, 1], mask=[False, side == "train"])
    test = np.ma.array([3, 4], mask=[False, side == "test"])
    with pytest.raises(ValueError, match="masked"):
        evaluate(mode, train, test, benchmark=np.ones(6))


@pytest.mark.parametrize("mode", ["walk", "purged"])
@pytest.mark.parametrize("dtype", [np.int64, np.uint64])
@pytest.mark.parametrize("with_benchmark", [False, True])
def test_all_false_split_masks_preserve_complete_result(
    mode: str, dtype: type, with_benchmark: bool
) -> None:
    train = np.array([0, 1], dtype=dtype)
    test = np.array([3, 4], dtype=dtype)
    benchmark = np.array([0.01, 0.02, 0.01, 0.03, 0.02, 0.01]) if with_benchmark else None
    expected = evaluate(mode, train, test, benchmark=benchmark)
    actual = evaluate(
        mode, np.ma.array(train, mask=False), np.ma.array(test, mask=False), benchmark=benchmark
    )
    assert actual.model_dump_json() == expected.model_dump_json()


def test_purged_mask_refusal_precedes_empty_fold_drop() -> None:
    splits = [
        (np.array([], dtype=int), np.ma.array([3, 4], mask=[False, True])),
        (np.array([0, 1]), np.array([3, 4])),
    ]
    with pytest.raises(ValueError, match="masked"):
        pcv.purged_cv_evaluate(PERFORMANCE, splits, embargo=1)


def test_complete_empty_purged_fold_still_drops() -> None:
    complete = [(np.array([0, 1]), np.array([3, 4]))]
    masked_empty = [(np.ma.array([], dtype=int, mask=False), np.ma.array([3, 4], mask=False))]
    expected = pcv.purged_cv_evaluate(PERFORMANCE, complete, embargo=1)
    actual = pcv.purged_cv_evaluate(PERFORMANCE, masked_empty + complete, embargo=1)
    assert actual.model_dump_json() == expected.model_dump_json()


@pytest.mark.parametrize("mode", ["walk", "purged"])
def test_known_row_geometry_refusal_retains_precedence(mode: str) -> None:
    train = np.ma.array([3, 4], mask=[False, True])
    test = np.array([1, 2])
    with pytest.raises(ValueError, match="precede" if mode == "walk" else "embargo"):
        evaluate(mode, train, test)


@pytest.mark.parametrize("mode", ["walk", "purged"])
def test_matrix_shape_refusal_retains_precedence(mode: str) -> None:
    splits = [(np.ma.array([0, 1], mask=True), np.array([3, 4]))]
    with pytest.raises(ValueError, match="configurations"):
        if mode == "walk":
            wf.walk_forward_evaluate(PERFORMANCE[:, :1], splits)
        else:
            pcv.purged_cv_evaluate(PERFORMANCE[:, :1], splits, embargo=1)


@pytest.mark.parametrize("mode", ["walk", "purged"])
@given(st.lists(st.booleans(), min_size=4, max_size=4))
def test_split_masks_refuse_any_missing_identity_and_preserve_complete_masks(
    mode: str, mask: list[bool]
) -> None:
    train = np.ma.array([0, 1], mask=mask[:2])
    test = np.ma.array([3, 4], mask=mask[2:])
    if any(mask):
        with pytest.raises(ValueError, match="masked"):
            evaluate(mode, train, test)
    else:
        assert (
            evaluate(mode, train, test).model_dump_json()
            == evaluate(mode, np.array([0, 1]), np.array([3, 4])).model_dump_json()
        )
