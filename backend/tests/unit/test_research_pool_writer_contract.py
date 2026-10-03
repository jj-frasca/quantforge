"""Static single-publisher contract for ADR-154's research pool."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_daily_discovery_is_the_only_workflow_that_stages_the_research_pool() -> None:
    publishers = {
        path.name
        for path in WORKFLOWS.glob("*.yml")
        if "git add data/research_pool" in path.read_text(encoding="utf-8")
    }

    assert publishers == {"daily-discovery.yml"}


def test_no_local_hunt_fallback_commits_the_research_pool() -> None:
    assert not (ROOT / "backend" / "scripts" / "cron_hunt.sh").exists()


def test_daily_discovery_universe_contains_the_former_weekly_universe() -> None:
    universe_dir = ROOT / "data" / "universes"
    daily = set((universe_dir / "discovery.txt").read_text(encoding="utf-8").splitlines())
    weekly = set((universe_dir / "sp500.txt").read_text(encoding="utf-8").splitlines())

    assert weekly <= daily
