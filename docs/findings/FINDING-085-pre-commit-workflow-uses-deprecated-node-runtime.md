# FINDING-085: The pre-commit workflow uses deprecated Node 20 actions

- **Severity:** Medium — GitHub is forcing deprecated action runtimes forward at execution time
- **Status:** Resolved
- **Date:** 2026-10-02
- **Affects:** `.github/workflows/pre-commit.yml`

## Finding

Every master pre-commit run emits a GitHub warning that `actions/setup-python@v5` and
`actions/cache@v4` target Node 20 and are being forced to Node 24. The repository does not name the
cache action directly: `pre-commit/action@v3.0.1` is a composite action that installs pre-commit,
caches `~/.cache/pre-commit` with `actions/cache@v4`, and runs all hooks.

Official action metadata provides Node 24 replacements. `actions/setup-python@v6` changes its
runtime from Node 20 to Node 24 without changing this workflow's Python-version input, and
`actions/cache@v5` runs on Node 24. GitHub-hosted `ubuntu-latest` satisfies their runner-version
requirement.

## Required correction

Replace `setup-python@v5` with `setup-python@v6`. Inline the three transparent steps from the
unmaintained pre-commit composite action—install pre-commit, cache its environment, and run all
hooks—while selecting `actions/cache@v5`. Preserve the workflow's permissions, concurrency,
Python 3.12 selection, cache key semantics, and hook command.

Add a static workflow contract that rejects the deprecated wrappers and requires the Node 24 action
majors plus the unchanged hook invocation. Do not change any hook, threshold, or dependency lock.
