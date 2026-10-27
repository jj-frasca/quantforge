"""Exclusive evidence claims, ordered sync requests, and retained failures."""

import os
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Self

import pytest

from app.research.lab.evidence_io import write_exclusive_bytes


@pytest.mark.parametrize("payload", [b"", b"\x00\xff\r\n", "résumé\n".encode()])
def test_write_exclusive_bytes_preserves_exact_payload(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "evidence.bin"
    write_exclusive_bytes(path, payload)
    assert path.read_bytes() == payload


def test_write_exclusive_bytes_refuses_existing_file_without_mutation(tmp_path: Path) -> None:
    path = tmp_path / "evidence.bin"
    path.write_bytes(b"original")
    with pytest.raises(FileExistsError):
        write_exclusive_bytes(path, b"replacement")
    assert path.read_bytes() == b"original"


@pytest.mark.parametrize("target_exists", [False, True])
def test_write_exclusive_bytes_refuses_symlink_without_touching_target(
    tmp_path: Path, target_exists: bool
) -> None:
    target = tmp_path / "target.bin"
    if target_exists:
        target.write_bytes(b"original")
    path = tmp_path / "evidence.bin"
    path.symlink_to(target)
    with pytest.raises(FileExistsError):
        write_exclusive_bytes(path, b"replacement")
    assert path.is_symlink()
    assert target.read_bytes() == b"original" if target_exists else not target.exists()


def test_write_exclusive_bytes_requires_existing_parent(tmp_path: Path) -> None:
    path = tmp_path / "absent" / "evidence.bin"
    with pytest.raises(FileNotFoundError):
        write_exclusive_bytes(path, b"payload")
    assert not path.parent.exists()


class _RecordedFile:
    def __init__(self, stream: BinaryIO, events: list[str], failure: str | None) -> None:
        self.stream = stream
        self.events = events
        self.failure = failure

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stream.close()
        self.events.append("file_close")
        if self.failure == "file_close":
            raise OSError("injected file_close")

    def write(self, payload: bytes) -> int:
        self.events.append("write")
        if self.failure in {"write", "short_write"}:
            self.stream.write(payload[:2])
            if self.failure == "write":
                raise OSError("injected write")
            return 2
        return self.stream.write(payload)

    def flush(self) -> None:
        self.events.append("flush")
        if self.failure == "flush":
            raise OSError("injected flush")
        self.stream.flush()

    def fileno(self) -> int:
        return self.stream.fileno()


@pytest.mark.parametrize(
    "failure",
    [
        None,
        "write",
        "short_write",
        "flush",
        "file_sync",
        "file_close",
        "parent_open",
        "parent_sync",
        "parent_close",
    ],
)
def test_write_exclusive_bytes_orders_sync_and_retains_failed_claims(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: str | None
) -> None:
    path = tmp_path / "evidence.bin"
    payload = b"complete payload\n"
    events: list[str] = []
    parent_fds: list[int] = []
    original_open = Path.open
    original_os_open = os.open
    original_close = os.close

    def open_file(p: Path, mode: str) -> _RecordedFile:
        assert p == path and mode == "xb"
        return _RecordedFile(original_open(p, mode), events, failure)

    def open_parent(p: Path, flags: int) -> int:
        events.append("parent_open")
        assert p == path.parent and flags == os.O_RDONLY
        assert events[-2] == "file_close"
        if failure == "parent_open":
            raise OSError("injected parent_open")
        fd = original_os_open(p, flags)
        parent_fds.append(fd)
        return fd

    def sync(fd: int) -> None:
        stage = "parent_sync" if parent_fds else "file_sync"
        events.append(stage)
        assert path.read_bytes() == payload  # File buffer was flushed before its sync.
        if failure == stage:
            raise OSError(f"injected {stage}")

    def close_parent(fd: int) -> None:
        assert fd == parent_fds[0]
        original_close(fd)
        events.append("parent_close")
        if failure == "parent_close":
            raise OSError("injected parent_close")

    # Keep reads unpatched; only the exclusive-claim open is intercepted.
    def patched_open(p: Path, mode: str = "r", *args: object, **kwargs: object) -> object:
        if mode == "xb":
            return open_file(p, mode)
        return original_open(p, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", patched_open)
    monkeypatch.setattr(os, "open", open_parent)
    monkeypatch.setattr(os, "fsync", sync)
    monkeypatch.setattr(os, "close", close_parent)

    if failure is None:
        write_exclusive_bytes(path, payload)
    else:
        message = "incomplete" if failure == "short_write" else f"injected {failure}"
        with pytest.raises(OSError, match=message):
            write_exclusive_bytes(path, payload)

    full_order = [
        "write",
        "flush",
        "file_sync",
        "file_close",
        "parent_open",
        "parent_sync",
        "parent_close",
    ]
    if failure in {"write", "short_write"}:
        expected = ["write", "file_close"]
    elif failure in {"flush", "file_sync"}:
        expected = [*full_order[: full_order.index(failure) + 1], "file_close"]
    elif failure == "parent_sync" or failure is None:
        expected = full_order
    else:
        expected = full_order[: full_order.index(failure) + 1]
    assert events == expected
    assert path.read_bytes() == (payload[:2] if failure in {"write", "short_write"} else payload)
    for fd in parent_fds:
        with pytest.raises(OSError):
            os.fstat(fd)

    # Retrying the same name cannot hide a failure, including an incomplete write.
    before_retry = list(events)
    with pytest.raises(FileExistsError):
        write_exclusive_bytes(path, b"replacement")
    assert events == before_retry
