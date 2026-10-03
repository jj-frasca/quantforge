"""Static causal-ordering contract for ADR-153's paper broker."""

from pathlib import Path

WORKFLOW_PATH = Path(__file__).resolve().parents[3] / ".github" / "workflows" / "paper-broker.yml"


def _workflow() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


def test_paper_broker_runs_only_after_successful_accrual_or_manual_recovery() -> None:
    workflow = _workflow()

    assert "workflow_run:" in workflow
    assert "workflows: [Paper forward accrual]" in workflow
    assert "types: [completed]" in workflow
    assert "schedule:" not in workflow
    assert "github.event_name == 'workflow_dispatch'" in workflow
    assert "github.event.workflow_run.conclusion == 'success'" in workflow


def test_paper_broker_resolves_current_master_when_the_job_starts() -> None:
    workflow = _workflow()

    checkout = workflow.split("- uses: actions/checkout@v5", 1)[1].split("\n\n", 1)[0]
    assert "ref: master" in checkout
