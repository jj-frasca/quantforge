"""Static production-writer contract for ADR-152."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_paper_forward_is_the_only_workflow_that_writes_the_paper_portfolio() -> None:
    assert "data/paper_portfolio.json" in _source(".github/workflows/paper-forward.yml")

    discovery = ".github/workflows/daily-discovery.yml"
    assert "paper_portfolio.json" not in _source(discovery), discovery


def test_discovery_and_local_hunt_scripts_do_not_write_the_paper_portfolio() -> None:
    for relative_path in (
        "backend/scripts/consolidate_pool.py",
        "backend/scripts/hunt.py",
    ):
        assert "paper_portfolio.json" not in _source(relative_path), relative_path


def test_paper_forward_reconciles_every_committed_pool_graduate() -> None:
    workflow = _source(".github/workflows/paper-forward.yml")
    paper_driver = _source("backend/scripts/paper.py")

    assert "scripts/paper.py" in workflow
    assert "PartitionedExperimentStore(POOL)" in paper_driver
    assert "experiments = pool.all()" in paper_driver
    assert "manage_portfolio(" in paper_driver
