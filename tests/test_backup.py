"""Backup logic is tested against an in-memory fake — no hardware required."""

from pathlib import Path
from typing import Dict, List, Tuple

from flipperkit.backup import sync


class FakeFlipper:
    """A tiny in-memory stand-in for the Flipper serial client.

    ``tree`` maps a directory path to a list of (name, is_dir, size) entries;
    ``files`` maps a full file path to its byte content.
    """

    def __init__(self, tree: Dict[str, List[Tuple[str, bool, int]]], files: Dict[str, bytes]):
        self.tree = tree
        self.files = files
        self.reads: List[str] = []

    def list_dir(self, path: str) -> List[Tuple[str, bool, int]]:
        return self.tree.get(path, [])

    def read_file(self, path: str) -> bytes:
        self.reads.append(path)
        return self.files[path]


def _sample_device() -> FakeFlipper:
    tree = {
        "/ext": [("nfc", True, 0), ("readme.txt", False, 5)],
        "/ext/nfc": [("card.nfc", False, 12)],
    }
    files = {
        "/ext/readme.txt": b"hello",
        "/ext/nfc/card.nfc": b"Filetype: x\n",
    }
    return FakeFlipper(tree, files)


def test_sync_downloads_recursively(tmp_path):
    fs = _sample_device()
    result = sync(fs, tmp_path)

    assert (tmp_path / "readme.txt").read_bytes() == b"hello"
    assert (tmp_path / "nfc" / "card.nfc").exists()
    assert len(result.downloaded) == 2
    assert result.bytes_written == len(b"hello") + len(b"Filetype: x\n")
    assert (tmp_path / "flipperkit-manifest.json").exists()


def test_sync_skips_unchanged_by_size(tmp_path):
    fs = _sample_device()
    sync(fs, tmp_path)
    fs.reads.clear()

    # Second run: sizes match, so nothing should be re-read from the device.
    result = sync(fs, tmp_path)
    assert result.downloaded == []
    assert len(result.skipped) == 2
    assert fs.reads == []


def test_sync_force_redownloads(tmp_path):
    fs = _sample_device()
    sync(fs, tmp_path)
    fs.reads.clear()

    result = sync(fs, tmp_path, force=True)
    assert len(result.downloaded) == 2
    assert len(fs.reads) == 2
