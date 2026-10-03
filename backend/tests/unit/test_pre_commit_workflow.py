"""Static runtime contract for FINDING-085's pre-commit workflow."""

from pathlib import Path

WORKFLOW = (
    Path(__file__).resolve().parents[3] / ".github" / "workflows" / "pre-commit.yml"
).read_text(encoding="utf-8")


def test_pre_commit_workflow_uses_node_24_action_majors() -> None:
    assert "actions/setup-python@v6" in WORKFLOW
    assert "actions/cache@v5" in WORKFLOW
    assert "actions/setup-python@v5" not in WORKFLOW
    assert "pre-commit/action@" not in WORKFLOW


def test_pre_commit_workflow_preserves_hook_and_cache_contract() -> None:
    assert 'python-version: "3.12"' in WORKFLOW
    assert "python -m pip install pre-commit" in WORKFLOW
    assert "path: ~/.cache/pre-commit" in WORKFLOW
    assert "hashFiles('.pre-commit-config.yaml')" in WORKFLOW
    assert "pre-commit run --show-diff-on-failure --color=always --all-files" in WORKFLOW
