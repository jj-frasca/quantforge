"""Production CLI boundary for ADR-081 complete-panel scratch shards."""

from pathlib import Path

import pytest
from scripts import run_panel_null_batch as batch_module
from scripts.run_panel_null_batch import DATA_ROOT, resolve_panel_indices


def test_resolve_panel_indices_accepts_a_unique_set_or_half_open_range() -> None:
    assert resolve_panel_indices(indices=[7, 2, 9], panel_range=None) == (7, 2, 9)
    assert resolve_panel_indices(indices=None, panel_range=[3, 7]) == (3, 4, 5, 6)


@pytest.mark.parametrize(
    ("indices", "panel_range", "message"),
    [
        ([], None, "at least one"),
        ([1, 1], None, "duplicate"),
        ([-1], None, "non-negative"),
        (None, [4], "exactly START STOP"),
        (None, [-1, 4], "non-negative"),
        (None, [4, 4], "greater than START"),
        (None, [5, 4], "greater than START"),
        ([1], [2, 3], "exactly one"),
        (None, None, "exactly one"),
    ],
)
def test_resolve_panel_indices_rejects_ambiguous_or_invalid_selections(
    indices: list[int] | None,
    panel_range: list[int] | None,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        resolve_panel_indices(indices=indices, panel_range=panel_range)


@pytest.mark.parametrize(
    "output_path",
    [
        DATA_ROOT / "panel_null_calibration" / "shard.json",
        DATA_ROOT,
    ],
)
def test_cli_refuses_generated_data_outputs_before_running(
    output_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called = False

    def run(*args: object, **kwargs: object) -> None:
        del args, kwargs
        nonlocal called
        called = True

    monkeypatch.setattr(batch_module, "run_production_panel_null_batch", run)

    with pytest.raises(ValueError, match="scratch-only"):
        batch_module.main(
            [
                "cohort.json",
                "source.npz",
                str(output_path),
                "--code-revision",
                "1" * 40,
                "--indices",
                "0",
            ]
        )
    assert not called


def test_cli_refuses_an_existing_output_before_running(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_path = tmp_path / "shard.json"
    output_path.write_text("occupied", encoding="utf-8")
    called = False

    def run(*args: object, **kwargs: object) -> None:
        del args, kwargs
        nonlocal called
        called = True

    monkeypatch.setattr(batch_module, "run_production_panel_null_batch", run)

    with pytest.raises(FileExistsError):
        batch_module.main(
            [
                "cohort.json",
                "source.npz",
                str(output_path),
                "--code-revision",
                "1" * 40,
                "--range",
                "0",
                "2",
            ]
        )
    assert not called


@pytest.mark.parametrize(
    ("selection", "expected"),
    [
        (["--indices", "7", "2", "9"], (7, 2, 9)),
        (["--range", "3", "7"], (3, 4, 5, 6)),
    ],
)
def test_cli_runs_current_production_policy_with_only_the_requested_complete_panels(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    selection: list[str],
    expected: tuple[int, ...],
) -> None:
    captured: dict[str, object] = {}

    def run(cohort_path: Path, source_path: Path, **kwargs: object) -> None:
        captured["cohort_path"] = cohort_path
        captured["source_path"] = source_path
        captured.update(kwargs)

    monkeypatch.setattr(batch_module, "run_production_panel_null_batch", run)
    output_path = tmp_path / "new" / "shard.json"

    batch_module.main(
        [
            "cohort.json",
            "source.npz",
            str(output_path),
            "--code-revision",
            "1" * 40,
            *selection,
        ]
    )

    assert captured["cohort_path"] == Path("cohort.json")
    assert captured["source_path"] == Path("source.npz")
    assert captured["panel_indices"] == expected
    assert captured["output_path"] == output_path
    assert captured["code_revision"] == "1" * 40
    assert captured["strategy_names"] == [entry.name for entry in batch_module.STRATEGY_CATALOG]
    config = captured["config"]
    assert isinstance(config, batch_module.GateConfig)
    assert output_path.parent.is_dir()
