"""Static safety contract for ADR-151's queued paper accrual."""

from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "paper-forward.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_paper_forward_resolves_current_master_after_concurrency_wait() -> None:
    workflow = _workflow()

    assert "group: paper-forward" in workflow
    assert "cancel-in-progress: false" in workflow
    checkout = workflow.split("- uses: actions/checkout@v5", 1)[1].split("\n\n", 1)[0]
    assert "ref: master" in checkout
