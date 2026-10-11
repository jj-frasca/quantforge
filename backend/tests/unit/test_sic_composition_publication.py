"""ADR-161's completed single look cannot be rerun or replaced (ADR-242)."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from scripts import sic_composition_test as driver


@pytest.mark.parametrize("kind", ["file", "malformed", "directory", "symlink", "dangling"])
def test_existing_result_refuses_before_any_input_or_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    out = tmp_path / "result.json"
    original = b"\x00not a JSON result" if kind == "malformed" else b"published bytes\n"
    target = tmp_path / "target"
    if kind in {"file", "malformed"}:
        out.write_bytes(original)
    elif kind == "directory":
        out.mkdir()
    elif kind == "symlink":
        target.write_bytes(original)
        out.symlink_to(target)
    else:
        out.symlink_to(target)
    store = Mock(side_effect=AssertionError("must not construct input store"))
    inference = Mock(side_effect=AssertionError("must not recompute a published look"))
    monkeypatch.setattr(driver, "OUT", out)
    monkeypatch.setattr(driver, "DATA", tmp_path / "absent inputs")
    monkeypatch.setattr(driver, "PartitionedExperimentStore", store)
    monkeypatch.setattr(driver, "run_test", inference)

    assert driver.main() != 0
    store.assert_not_called()
    inference.assert_not_called()
    if kind in {"file", "malformed", "symlink"}:
        assert out.read_bytes() == original
    elif kind == "directory":
        assert out.is_dir()
        assert list(out.iterdir()) == []
    else:
        assert out.is_symlink()
        assert not target.exists()


def synthetic_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Mock, Mock]:
    out = tmp_path / "output" / "result.json"
    (tmp_path / "fundamentals_pool.json").write_text(
        json.dumps([{"symbol": "X", "sic_code": "2000"}])
    )
    store = Mock(return_value=SimpleNamespace(all=lambda: []))
    inference = Mock(return_value={"reading": "synthetic result only"})
    monkeypatch.setattr(driver, "OUT", out)
    monkeypatch.setattr(driver, "DATA", tmp_path)
    monkeypatch.setattr(driver, "PartitionedExperimentStore", store)
    monkeypatch.setattr(driver, "_matched", lambda *_: [SimpleNamespace(symbol="X")])
    monkeypatch.setattr(driver, "_per_symbol_excess", lambda *_: {"X": 0.1})
    monkeypatch.setattr(driver, "run_test", inference)
    return out, store, inference


def test_first_publication_retains_json_and_second_invocation_cannot_recompute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out, store, inference = synthetic_inputs(tmp_path, monkeypatch)
    assert driver.main() == 0
    original = out.read_bytes()
    result = json.loads(original)
    assert result == {
        "reading": "synthetic result only",
        "cohorts": {
            str(bars): {
                "matched": 1,
                "absent_from_fundamentals_pool": 0,
                "pool_row_without_sic_code": 0,
                "used": 1,
            }
            for bars in (7400, 9247)
        },
        "restriction": "fundamentals-eligible symbols only (ADR-161 section 7)",
    }
    store.reset_mock()
    inference.reset_mock()
    assert driver.main() != 0
    store.assert_not_called()
    inference.assert_not_called()
    assert out.read_bytes() == original


def test_late_competing_publication_preserves_winner_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out, _, inference = synthetic_inputs(tmp_path, monkeypatch)
    original = b"late published result\n"

    def compete(*_: object) -> dict[str, str]:
        out.parent.mkdir()
        out.write_bytes(original)
        return {"reading": "losing synthetic result"}

    inference.side_effect = compete
    assert driver.main() != 0
    assert out.read_bytes() == original


def test_unmet_run_gate_still_refuses_without_inference_or_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    out, _, inference = synthetic_inputs(tmp_path, monkeypatch)
    (tmp_path / "fundamentals_pool.json").write_text(json.dumps([{"symbol": "X"}]))
    assert driver.main() != 0
    inference.assert_not_called()
    assert not out.exists()
