import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.research.lab.sic_composition import (
    Member,
    classify,
    collapse,
    post_stratified_mean,
    run_test,
    sic_division,
)


@pytest.mark.parametrize(
    ("code", "division"),
    [
        ("0100", "A"),
        ("1311", "B"),
        ("1531", "C"),
        ("2834", "D"),
        ("3826", "D"),
        ("4813", "E"),
        ("5045", "F"),
        ("5812", "G"),
        ("6021", "H"),
        ("7372", "I"),
        ("8071", "I"),
        ("9100", "J"),
    ],
)
def test_division_follows_the_sec_major_group_ranges(code: str, division: str) -> None:
    assert sic_division(code) == division


@pytest.mark.parametrize("code", [None, "", "abcd", "1", "1900", "6800x", "00"])
def test_unmapped_codes_are_dropped_not_guessed(code: str | None) -> None:
    assert sic_division(code) is None


@given(st.integers(min_value=1, max_value=99))
def test_division_is_total_over_valid_major_groups_except_the_gaps(major: int) -> None:
    gaps = set(range(18, 20)) | set(range(68, 70)) | set(range(90, 91))
    result = sic_division(f"{major:02d}00")
    assert (result is None) == (major in gaps)


def test_small_divisions_collapse_into_other_across_both_cohorts() -> None:
    a = [Member("D", 0.0)] * 5 + [Member("A", 0.0)] * 2
    b = [Member("D", 0.0)] * 5 + [Member("A", 0.0)] * 2 + [Member("B", 0.0)] * 5
    ca, cb = collapse(a, b)
    assert {m.division for m in ca} == {"D", "Other"}
    assert {m.division for m in cb} == {"D", "Other", "B"}


def test_post_stratified_mean_against_own_weights_is_the_mean() -> None:
    members = [Member("D", 1.0), Member("D", 3.0), Member("H", -1.0)]
    assert post_stratified_mean(members, members) == pytest.approx(np.mean([1.0, 3.0, -1.0]))


def test_post_stratified_mean_reweights_to_target_divisions() -> None:
    source = [Member("D", 1.0), Member("H", 5.0), Member("H", 5.0), Member("H", 5.0)]
    target = [Member("D", 0.0), Member("H", 0.0)]
    assert post_stratified_mean(source, target) == pytest.approx(3.0)


def test_post_stratified_mean_ignores_divisions_absent_from_source() -> None:
    source = [Member("D", 2.0)]
    target = [Member("D", 0.0), Member("H", 0.0)]
    assert post_stratified_mean(source, target) == pytest.approx(2.0)


def test_classify_explains_when_composition_closes_the_gap() -> None:
    assert classify((0.05, 0.12), 0.01, (-0.03, 0.04), raw=0.08, adjusted=0.02) == "explains"


def test_classify_does_not_explain_when_gap_survives() -> None:
    assert classify((0.05, 0.12), 0.40, (0.04, 0.11), raw=0.08, adjusted=0.07) == "does_not_explain"


def test_classify_is_inconclusive_when_raw_gap_includes_zero() -> None:
    assert classify((-0.02, 0.10), 0.01, (-0.03, 0.04), raw=0.04, adjusted=0.0) == "inconclusive"


def _cohort(rng: np.random.Generator, shift: float, n: int = 40) -> list[Member]:
    divs = rng.choice(["D", "H", "I"], size=n)
    return [Member(str(d), float(rng.normal(shift, 0.2))) for d in divs]


def test_run_test_is_deterministic_and_reports_both_cohorts() -> None:
    rng = np.random.default_rng(0)
    a, b = _cohort(rng, -0.12), _cohort(rng, -0.05)
    r1 = run_test(a, b, draws=300)
    r2 = run_test(a, b, draws=300)
    assert r1 == r2
    assert r1["n"] == {"a": 40, "b": 40}
    assert r1["reading"] in {"explains", "does_not_explain", "inconclusive"}
    assert 0.0 <= r1["s1_p"] <= 1.0


def test_run_test_detects_a_composition_difference() -> None:
    a = [Member("D", 0.0)] * 30 + [Member("H", 0.0)] * 5
    b = [Member("D", 0.0)] * 5 + [Member("H", 0.0)] * 30
    assert run_test(a, b, draws=500)["s1_p"] < 0.05
