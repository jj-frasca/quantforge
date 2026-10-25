"""Regression floors for packages named by FINDING-086/313/314 Dependabot alerts."""

import json
import tomllib
from pathlib import Path

import pytest
from packaging.version import Version

LOCK_PATH = Path(__file__).resolve().parents[2] / "uv.lock"
PATCHED_MINIMUMS = {
    "anyio": Version("4.14.2"),
    "certifi": Version("2026.10.19"),
    "filelock": Version("4.2.1"),
    "pydantic-settings": Version("2.14.2"),
    "soupsieve": Version("2.9.0"),
    "virtualenv": Version("21.14.13"),
}


@pytest.mark.parametrize(("package", "minimum"), PATCHED_MINIMUMS.items())
def test_alerted_packages_are_locked_at_patched_versions(package: str, minimum: Version) -> None:
    lock = tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))
    versions = {package["name"]: Version(package["version"]) for package in lock["package"]}

    assert versions[package] >= minimum, f"{package} must be >= {minimum}"


@pytest.mark.parametrize(
    ("package", "minimum"), [("zod", Version("4.6.7")), ("undici", Version("7.30.1"))]
)
def test_alerted_frontend_packages_are_locked_at_patched_versions(
    package: str, minimum: Version
) -> None:
    lock_path = LOCK_PATH.parent.parent / "frontend" / "package-lock.json"
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    matches = [
        Version(record["version"])
        for path, record in lock["packages"].items()
        if path.endswith(f"node_modules/{package}")
    ]
    assert matches, f"{package} is absent from the frontend lock"
    assert all(version >= minimum for version in matches), f"{package} must be >= {minimum}"
