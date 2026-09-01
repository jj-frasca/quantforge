"""Repository documentation identities are coordination keys, not decorative labels."""

import re
from collections import defaultdict
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ("directory", "prefix", "legacy_duplicates"),
    [
        (
            "docs/adr",
            "ADR",
            {
                "023": [
                    "ADR-023-forward-equity-series.md",
                    "ADR-023-value-prescreen-into-the-hunt.md",
                ]
            },
        ),
        ("docs/findings", "FINDING", {}),
    ],
)
def test_document_numbers_are_unique(
    directory: str, prefix: str, legacy_duplicates: dict[str, list[str]]
) -> None:
    numbered_paths: dict[str, list[str]] = defaultdict(list)
    pattern = re.compile(rf"^{prefix}-(\d{{3}})-")

    for path in sorted((REPO_ROOT / directory).glob("*.md")):
        match = pattern.match(path.name)
        if match is not None:
            numbered_paths[match.group(1)].append(path.name)

    duplicates = {number: paths for number, paths in numbered_paths.items() if len(paths) > 1}
    assert duplicates == legacy_duplicates, f"new duplicate {prefix} identities: {duplicates}"
