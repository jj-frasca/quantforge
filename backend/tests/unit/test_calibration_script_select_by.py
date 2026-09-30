"""`--select-by` CLI parsing (ADR-069) is identical, copy-pasted logic in both
scripts/null_calibration.py and scripts/power_calibration.py. Neither driver script runs in CI
(expensive, real searches), but the pure argv-parsing helper is cheap and worth locking down
directly, matching the existing scripts.* import convention in test_consolidate_null_calibration.py.
"""

import pytest
from scripts.null_calibration import _select_by as null_select_by
from scripts.power_calibration import _select_by as power_select_by


@pytest.mark.parametrize("select_by", [null_select_by, power_select_by])
@pytest.mark.parametrize("value", ["observed", "walk_forward"])
def test_select_by_accepts_the_two_valid_arms(
    monkeypatch: pytest.MonkeyPatch,
    select_by: object,
    value: str,
) -> None:
    monkeypatch.setattr("sys.argv", ["script", "--select-by", value])
    assert select_by() == value  # type: ignore[operator]


@pytest.mark.parametrize("select_by", [null_select_by, power_select_by])
def test_select_by_defaults_to_observed(monkeypatch: pytest.MonkeyPatch, select_by: object) -> None:
    monkeypatch.setattr("sys.argv", ["script"])
    assert select_by() == "observed"  # type: ignore[operator]


@pytest.mark.parametrize("select_by", [null_select_by, power_select_by])
def test_select_by_rejects_a_typo_rather_than_defaulting(
    monkeypatch: pytest.MonkeyPatch, select_by: object
) -> None:
    monkeypatch.setattr("sys.argv", ["script", "--select-by", "observd"])
    with pytest.raises(SystemExit, match="observd"):
        select_by()  # type: ignore[operator]
