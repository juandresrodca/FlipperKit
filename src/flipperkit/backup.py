"""Back up the Flipper SD card to a local folder.

The sync logic depends only on the small :class:`RemoteFS` protocol, so it can
be driven by a real :class:`~flipperkit.client.FlipperClient` or by a fake in
tests. Unchanged files (matched by size) are skipped unless ``force`` is set.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Tuple

try:
    from typing import Protocol
except ImportError:  # pragma: no cover
    Protocol = object  # type: ignore


class RemoteFS(Protocol):
    """The device-side interface the backup logic requires."""

    def list_dir(self, path: str) -> List[Tuple[str, bool, int]]: ...

    def read_file(self, path: str) -> bytes: ...


@dataclass
class BackupResult:
    downloaded: List[str] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    errors: List[Tuple[str, str]] = field(default_factory=list)
    bytes_written: int = 0

    @property
    def summary(self) -> dict:
        return {
            "downloaded": len(self.downloaded),
            "skipped": len(self.skipped),
            "errors": len(self.errors),
            "bytes_written": self.bytes_written,
        }


def _walk(fs: RemoteFS, root: str) -> List[Tuple[str, int]]:
    """Depth-first walk of the remote filesystem. Returns ``(path, size)``."""
    files: List[Tuple[str, int]] = []
    stack = [root]
    while stack:
        current = stack.pop()
        for name, is_dir, size in fs.list_dir(current):
            child = f"{current.rstrip('/')}/{name}"
            if is_dir:
                stack.append(child)
            else:
                files.append((child, size))
    return files


def sync(
    fs: RemoteFS,
    dest: Path,
    root: str = "/ext",
    force: bool = False,
    on_file: Optional[Callable[[str, str], None]] = None,
) -> BackupResult:
    """Mirror ``root`` from the device into ``dest``.

    ``on_file`` is called as ``on_file(remote_path, action)`` where action is
    ``"downloaded"`` or ``"skipped"`` — used by the CLI for progress output.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    result = BackupResult()

    for remote_path, remote_size in _walk(fs, root):
        rel = remote_path[len(root):].lstrip("/")
        local_path = dest / rel

        if not force and local_path.exists() and local_path.stat().st_size == remote_size:
            result.skipped.append(remote_path)
            if on_file:
                on_file(remote_path, "skipped")
            continue

        try:
            data = fs.read_file(remote_path)
        except Exception as exc:  # noqa: BLE001 - report per-file, keep going
            result.errors.append((remote_path, str(exc)))
            continue

        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(data)
        result.downloaded.append(remote_path)
        result.bytes_written += len(data)
        if on_file:
            on_file(remote_path, "downloaded")

    _write_manifest(dest, result)
    return result


def _write_manifest(dest: Path, result: BackupResult) -> None:
    manifest = dest / "flipperkit-manifest.json"
    manifest.write_text(json.dumps(result.summary, indent=2))
