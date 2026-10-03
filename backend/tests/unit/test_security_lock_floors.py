"""Regression floors for packages named by FINDING-086's Dependabot alerts."""

import tomllib
from pathlib import Path

from packaging.version import Version

LOCK_PATH = Path(__file__).resolve().parents[2] / "uv.lock"
PATCHED_MINIMUMS = {
    "anyio": Version("4.14.2"),
    "pydantic-settings": Version("2.14.2"),
    "soupsieve": Version("2.9.0"),
    "virtualenv": Version("21.7.13"),
}


def test_alerted_packages_are_locked_at_patched_versions() -> None:
    lock = tomllib.loads(LOCK_PATH.read_text(encoding="utf-8"))
    versions = {package["name"]: Version(package["version"]) for package in lock["package"]}

    for package, minimum in PATCHED_MINIMUMS.items():
        assert versions[package] >= minimum, f"{package} must be >= {minimum}"
