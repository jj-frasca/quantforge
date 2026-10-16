"""ADR-303: shared queued-start revision and attempt identity, entirely local."""

import os
import re
import subprocess
import textwrap
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parents[3] / ".github/workflows/daily-discovery.yml"


def _job(name: str) -> str:
    text = WORKFLOW.read_text()
    match = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z_]+:\n|\Z)", text, re.M | re.S)
    assert match is not None, f"missing required {name} job"
    return match.group(1)


def _script(job: str, step: str) -> str:
    # Assert the exact named safe step exists BEFORE extracting or executing anything.
    marker = f"      - name: {step}\n"
    body = _job(job)
    assert marker in body, f"missing required {step} step"
    block = body.split(marker, 1)[1].split("\n      - ", 1)[0]
    assert "        run: |\n" in block
    script = textwrap.dedent(block.split("        run: |\n", 1)[1])
    assert "${{" not in script, "executable fixture must not leave workflow expressions unresolved"
    return script


def _bash(script: str, root: Path, **values: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["/bin/bash", "-e", "-c", script],
        cwd=root,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", **values},
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], stderr=subprocess.STDOUT, text=True, timeout=20
    ).strip()


def _repo(root: Path, remote: Path) -> None:
    root.mkdir()
    _git(root, "init", "-b", "fixture")
    for key, value in [
        ("user.name", "local-test"),
        ("user.email", "local@example.invalid"),
        ("commit.gpgsign", "false"),
        ("core.hooksPath", "/dev/null"),
    ]:
        _git(root, "config", key, value)
    _git(root, "remote", "add", "origin", str(remote))


def test_discovery_prepares_one_fresh_master_revision_with_bounded_job() -> None:
    text = WORKFLOW.read_text()
    prepare = _job("prepare")
    assert "group: daily-discovery\n  cancel-in-progress: false" in text
    assert "timeout-minutes: 10" in prepare
    assert "ref: master" in prepare
    assert "revision: ${{ steps.freeze.outputs.revision }}" in prepare
    assert "attempt: ${{ steps.freeze.outputs.attempt }}" in prepare
    assert "id: freeze" in prepare
    script = _script("prepare", "Freeze shared discovery revision")
    assert "git rev-parse HEAD" in script


@pytest.mark.parametrize("job", ["discover", "consolidate"])
def test_discovery_consumers_preflight_before_same_immutable_checkout(job: str) -> None:
    body = _job(job)
    assert body.index("name: Validate shared discovery revision") < body.index(
        "uses: actions/checkout@v5"
    )
    assert "ref: ${{ needs.prepare.outputs.revision }}" in body
    assert "SHARED_REVISION: ${{ needs.prepare.outputs.revision }}" in body
    assert "PREPARED_ATTEMPT: ${{ needs.prepare.outputs.attempt }}" in body
    assert _script(job, "Validate shared discovery revision") == _script(
        "discover", "Validate shared discovery revision"
    )
    if job == "discover":
        assert "needs: prepare" in body
    else:
        assert "needs: [prepare, discover]" in body
        assert "if: ${{ always() && needs.prepare.result == 'success' }}" in body
        assert "needs.discover.result == 'success'" not in body


def test_discovery_current_attempt_artifacts_preserve_partial_shards_and_universe() -> None:
    discover = _job("discover")
    consolidate = _job("consolidate")
    assert "name: pool-${{ github.run_attempt }}-shard-${{ matrix.shard }}" in discover
    assert "pattern: pool-${{ github.run_attempt }}-shard-*" in consolidate
    assert "pattern: pool-shard-*" not in consolidate
    assert "always() && hashFiles(format('shard_{0}.json', matrix.shard)) != ''" in discover
    assert "github.event.inputs.universe || 'data/universes/discovery.txt'" in discover
    assert "shard: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]" in discover
    assert "for attempt in 1 2; do" in discover and "for attempt in 1 2; do" in consolidate
    assert "merge-multiple: true" in consolidate


@pytest.mark.parametrize("sha", ["", "a" * 39, "a" * 41, "A" * 40, "g" * 40, "not-a-revision"])
def test_discovery_preparation_rejects_malformed_head_without_outputs(
    tmp_path: Path, sha: str
) -> None:
    script = _script("prepare", "Freeze shared discovery revision")
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    fake = bin_path / "git"
    fake.write_text('#!/bin/bash\nprintf "%s\\n" "$FAKE_HEAD"\n')
    fake.chmod(0o755)
    output = tmp_path / "outputs"
    result = _bash(
        script,
        tmp_path,
        PATH=f"{bin_path}:{os.environ['PATH']}",
        FAKE_HEAD=sha,
        GITHUB_RUN_ATTEMPT="1",
        GITHUB_OUTPUT=str(output),
    )
    assert result.returncode != 0
    assert not output.exists() or not output.read_text()


@pytest.mark.parametrize("attempt", ["", "0", "01", "-1", "1.0", "true", " 1", "1\n2"])
def test_discovery_preparation_rejects_noncanonical_attempt(tmp_path: Path, attempt: str) -> None:
    script = _script("prepare", "Freeze shared discovery revision")
    bin_path = tmp_path / "bin"
    bin_path.mkdir()
    fake = bin_path / "git"
    fake.write_text('#!/bin/bash\nprintf "%s\\n" "$FAKE_HEAD"\n')
    fake.chmod(0o755)
    output = tmp_path / "outputs"
    result = _bash(
        script,
        tmp_path,
        PATH=f"{bin_path}:{os.environ['PATH']}",
        FAKE_HEAD="a" * 40,
        GITHUB_RUN_ATTEMPT=attempt,
        GITHUB_OUTPUT=str(output),
    )
    assert result.returncode != 0
    assert not output.exists() or not output.read_text()


@pytest.mark.parametrize("job", ["discover", "consolidate"])
@pytest.mark.parametrize(
    "sha,prepared,current",
    [
        ("", "1", "1"),
        ("a" * 39, "1", "1"),
        ("A" * 40, "1", "1"),
        ("a" * 40, "", "1"),
        ("a" * 40, "0", "1"),
        ("a" * 40, "01", "1"),
        ("a" * 40, "1", "2"),
        ("a" * 40, "2", ""),
        ("a" * 40, "2", "02"),
        ("a" * 40, "2", "1"),
    ],
)
def test_discovery_consumer_invalid_or_stale_identity_refuses_before_checkout(
    tmp_path: Path, job: str, sha: str, prepared: str, current: str
) -> None:
    script = _script(job, "Validate shared discovery revision")
    result = _bash(
        script, tmp_path, SHARED_REVISION=sha, PREPARED_ATTEMPT=prepared, GITHUB_RUN_ATTEMPT=current
    )
    assert result.returncode != 0
    assert "rerun all jobs" in (result.stdout + result.stderr).lower()


@pytest.mark.parametrize("job", ["discover", "consolidate"])
@pytest.mark.parametrize("attempt", ["1", "2", "9" * 50])
def test_discovery_consumer_valid_identity_accepts_exact_attempt_strings(
    tmp_path: Path, job: str, attempt: str
) -> None:
    result = _bash(
        _script(job, "Validate shared discovery revision"),
        tmp_path,
        SHARED_REVISION="a" * 40,
        PREPARED_ATTEMPT=attempt,
        GITHUB_RUN_ATTEMPT=attempt,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_discovery_fresh_shared_shallow_revision_and_actual_publication_script(
    tmp_path: Path,
) -> None:
    freeze = _script("prepare", "Freeze shared discovery revision")
    publish = _script("consolidate", "Commit pool (if changed)")
    assert "git switch -c discovery-publication" in publish
    assert "git push origin HEAD:master" in publish
    assert "--force" not in publish
    remote = tmp_path / "remote.git"
    remote.mkdir()
    _git(remote, "init", "--bare", "--initial-branch=master")
    seed = tmp_path / "seed"
    _repo(seed, remote)
    pool = seed / "data/research_pool"
    pool.mkdir(parents=True)
    (pool / "COUNTER.txt").write_text("100\n")
    (seed / "code.txt").write_text("version1\n")
    _git(seed, "add", "data/research_pool/COUNTER.txt", "code.txt")
    _git(seed, "commit", "-m", "event baseline")
    event = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "HEAD:master")
    (pool / "COUNTER.txt").write_text("104\n")
    _git(seed, "add", "data/research_pool/COUNTER.txt")
    _git(seed, "commit", "-m", "predecessor publishes104")
    fresh = _git(seed, "rev-parse", "HEAD")
    _git(seed, "push", "origin", "HEAD:master")
    prepare = tmp_path / "prepare"
    _repo(prepare, remote)
    _git(prepare, "fetch", "--depth=1", "origin", "master")
    _git(prepare, "checkout", "--detach", "FETCH_HEAD")
    out = tmp_path / "outputs"
    result = _bash(freeze, prepare, GITHUB_OUTPUT=str(out), GITHUB_RUN_ATTEMPT="2")
    assert result.returncode == 0, result.stdout + result.stderr
    outputs = dict(line.split("=", 1) for line in out.read_text().splitlines())
    assert outputs == {"revision": fresh, "attempt": "2"}
    old_prior = int(_git(seed, "show", f"{event}:data/research_pool/COUNTER.txt"))
    assert old_prior + 4 == 104
    (seed / "code.txt").write_text("version2\n")
    _git(seed, "add", "code.txt")
    _git(seed, "commit", "-m", "unrelated master advance")
    _git(seed, "push", "origin", "HEAD:master")
    for i in range(2):
        shard = tmp_path / f"shard{i}"
        _repo(shard, remote)
        _git(shard, "fetch", "--depth=1", "origin", outputs["revision"])
        _git(shard, "checkout", "--detach", "FETCH_HEAD")
        assert _git(shard, "rev-parse", "HEAD") == fresh
        assert (shard / "code.txt").read_text() == "version1\n"
        assert int((shard / "data/research_pool/COUNTER.txt").read_text()) + 4 == 108
    publisher = tmp_path / "publisher"
    _repo(publisher, remote)
    _git(publisher, "fetch", "--depth=1", "origin", fresh)
    _git(publisher, "checkout", "--detach", "FETCH_HEAD")
    (publisher / "data/research_pool/COUNTER.txt").write_text("108\n")
    result = _bash(publish, publisher)
    assert result.returncode == 0, result.stdout + result.stderr
    assert _git(remote, "show", "master:data/research_pool/COUNTER.txt") == "108"
    assert _git(remote, "show", "master:code.txt") == "version2"
    assert _git(publisher, "branch", "--show-current") == "discovery-publication"
    assert "refs/heads/discovery-publication" not in _git(remote, "show-ref")
