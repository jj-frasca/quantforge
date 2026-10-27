"""Exclusive byte creation with explicit POSIX synchronization requests (ADR-383)."""

import os
from pathlib import Path


def write_exclusive_bytes(path: Path, payload: bytes) -> None:
    """Write once, flush/sync the file, then sync its existing parent directory.

    Errors propagate and retain any created claim, possibly with partial bytes.
    Readers may observe partial files; this is not atomic publication or a
    guarantee of physical storage durability. Unsupported directory sync fails.
    """
    path = Path(path)
    with path.open("xb") as artifact:
        if artifact.write(payload) != len(payload):
            raise OSError("exclusive evidence write was incomplete")
        artifact.flush()
        os.fsync(artifact.fileno())

    parent_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)
