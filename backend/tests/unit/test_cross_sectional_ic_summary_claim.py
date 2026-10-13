"""Durable IC metadata domains and redundant statistic identity (ADR-267)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.research.cross_sectional.ic import ICSummary, summarize_ic
from app.research.cross_sectional.search import CrossSectionalExperiment, CrossSectionalTrial
from app.research.cross_sectional.store import JsonFileCrossSectionalStore
from app.research.lab.gate import GateConfig


def _valid(**updates: object) -> ICSummary:
    mean, std, n = 0.1, 0.2, 4
    return ICSummary.model_validate(
        {
            "mean": mean,
            "std": std,
            "information_ratio": mean / std,
            "t_stat": (mean / std) * float(np.sqrt(n)),
            "hit_rate": 0.5,
            "n_periods": n,
        }
        | updates
    )


_BAD = [
    (field, value)
    for field in ("mean", "std", "information_ratio", "t_stat", "hit_rate")
    for value in (float("nan"), float("inf"), float("-inf"))
] + [
    ("std", -0.1),
    ("hit_rate", -0.1),
    ("hit_rate", 1.1),
    ("n_periods", -1),
    ("n_periods", 0),
    ("n_periods", 1),
    ("n_periods", True),
    ("n_periods", np.bool_(True)),
    ("n_periods", 4.0),
    ("n_periods", "4"),
    ("n_periods", 10**1000),
    ("information_ratio", 99.0),
    ("t_stat", 99.0),
    ("information_ratio", np.nextafter(0.5, np.inf)),
    ("t_stat", np.nextafter(1.0, np.inf)),
]


@pytest.mark.parametrize(("field", "value"), _BAD)
def test_ic_leaf_rejects_invalid_original_claim(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _valid(**{field: value})


@pytest.mark.parametrize(("field", "value"), _BAD)
def test_ic_leaf_revalidates_unchecked_copy(field: str, value: object) -> None:
    bad = _valid().model_copy(update={field: value})
    with pytest.raises(ValidationError):
        ICSummary.model_validate(bad)


def _trial(ic: ICSummary | None) -> CrossSectionalTrial:
    return CrossSectionalTrial(
        strategy_name="xs_momentum",
        parameters={"lookback": 20},
        observed_sharpe=1.0,
        deflated_sharpe=0.5,
        pbo=0.1,
        parameter_stability_score=0.8,
        ic=ic,
    )


def _experiment(ic: ICSummary | None) -> CrossSectionalExperiment:
    return CrossSectionalExperiment(
        universe_symbols=["A", "B"],
        strategy_names=["xs_momentum"],
        gate_config=GateConfig(),
        trials=[_trial(ic)],
        lifetime_trials=1,
    )


@pytest.mark.parametrize(("field", "value"), _BAD)
def test_ic_leaf_nested_attachment_and_writer_refuse_before_mutation(
    field: str, value: object, tmp_path: Path
) -> None:
    good = _valid()
    bad = good.model_copy(update={field: value})
    with pytest.raises(ValidationError):
        _trial(bad)
    path = tmp_path / "claims.json"
    store = JsonFileCrossSectionalStore(path)
    original = _experiment(good)
    store.add(original)
    before = path.read_bytes()
    bad_trial = _trial(good).model_copy(update={"ic": bad})
    unchecked = original.model_copy(update={"trials": [bad_trial]})
    with pytest.raises(ValidationError):
        store.add(unchecked)
    assert path.read_bytes() == before
    assert store.all()[0].model_dump() == original.model_dump()
    absent = tmp_path / "uncreated" / "claims.json"
    with pytest.raises(ValidationError):
        JsonFileCrossSectionalStore(absent).add(unchecked)
    assert not absent.parent.exists()


@pytest.mark.parametrize("n", [2, 4, np.int64(4), np.uint64(4)])
def test_ic_leaf_preserves_native_integral_counts(n: object) -> None:
    summary = _valid(n_periods=n, t_stat=0.5 * float(np.sqrt(n)))
    assert type(summary.n_periods) is int
    assert summary.n_periods == n
    assert ICSummary.model_validate(summary).model_dump() == summary.model_dump()
    assert (
        ICSummary.model_validate_json(summary.model_dump_json()).model_dump()
        == summary.model_dump()
    )


@pytest.mark.parametrize(
    "values", [[0.0, 0.0], [0.25, 0.25], [-1.0, 1.0], [-1.0, -1.0], [0.25, -0.5, 0.75]]
)
def test_ic_leaf_retains_original_statistics_and_floor(values: list[float]) -> None:
    summary = summarize_ic(pd.Series(values))
    assert summary is not None
    mean, std = float(np.mean(values)), float(np.std(values, ddof=1))
    ir = mean / max(std, 1e-12)
    assert summary.model_dump() == {
        "mean": mean,
        "std": std,
        "information_ratio": ir,
        "t_stat": ir * float(np.sqrt(len(values))),
        "hit_rate": float(np.mean(np.array(values) > 0)),
        "n_periods": len(values),
    }


def test_ic_leaf_preserves_coherent_legacy_endpoint_without_new_tolerance() -> None:
    mean = float(np.nextafter(1.0, np.inf))
    ir = mean / 1e-12
    summary = _valid(
        mean=mean, std=0.0, information_ratio=ir, t_stat=ir * float(np.sqrt(4)), hit_rate=1.0
    )
    assert summary.mean == mean
    assert ICSummary.model_validate_json(summary.model_dump_json()).mean == mean


def test_ic_leaf_preserves_absent_legacy_measurement(tmp_path: Path) -> None:
    original = _experiment(None)
    store = JsonFileCrossSectionalStore(tmp_path / "legacy.json")
    store.add(original)
    assert store.all()[0].model_dump() == original.model_dump()
    assert store.all()[0].trials[0].ic is None


@settings(max_examples=60, deadline=None)
@given(
    st.lists(
        st.floats(min_value=-1, max_value=1, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=30,
    )
)
def test_ic_leaf_accepts_measured_bounded_observations_exactly(values: list[float]) -> None:
    summary = summarize_ic(pd.Series(values))
    assert summary is not None
    assert (
        ICSummary.model_validate_json(summary.model_dump_json()).model_dump()
        == summary.model_dump()
    )
