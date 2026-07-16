"""Parsers for Flipper Zero artifact files.

Most Flipper files are UTF-8 text using a simple ``Key: Value`` format with a
leading ``Filetype:`` header and ``#`` comment lines. This module turns those
files into normalized :class:`~flipperkit.models.FlipperRecord` objects.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Tuple, Union

from .models import FlipperRecord

# Coarse category keyed by file extension.
EXT_CATEGORY = {
    ".nfc": "nfc",
    ".sub": "subghz",
    ".rfid": "rfid",
    ".ir": "infrared",
    ".ibtn": "ibutton",
    ".u2f": "u2f",
}

Pairs = List[Tuple[str, str]]
PathLike = Union[str, Path]


def parse_kv_pairs(text: str) -> Pairs:
    """Parse Flipper ``Key: Value`` text into ordered pairs.

    Order and duplicate keys are preserved (infrared files repeat ``name:``,
    ``protocol:`` … once per stored signal). Comment and blank lines are
    dropped.
    """
    pairs: Pairs = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        pairs.append((key.strip(), value.strip()))
    return pairs


def first(pairs: Pairs, key: str, default: Optional[str] = None) -> Optional[str]:
    """Return the first value for ``key`` (case-sensitive), else ``default``."""
    for k, v in pairs:
        if k == key:
            return v
    return default


def all_values(pairs: Pairs, key: str) -> List[str]:
    """Return every value stored under ``key``, in order."""
    return [v for k, v in pairs if k == key]


def _to_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value.strip())
    except (ValueError, AttributeError):
        return None


def _extract(category: str, pairs: Pairs) -> Tuple[Optional[str], Optional[str], Optional[int], dict]:
    """Pull the category-specific subtype, identifier and frequency."""
    subtype: Optional[str] = None
    identifier: Optional[str] = None
    frequency: Optional[int] = None
    extra: dict = {}

    if category == "nfc":
        subtype = first(pairs, "Device type")
        identifier = first(pairs, "UID")
    elif category == "subghz":
        subtype = first(pairs, "Protocol")
        identifier = first(pairs, "Key")
        frequency = _to_int(first(pairs, "Frequency"))
        preset = first(pairs, "Preset")
        if preset:
            extra["preset"] = preset
    elif category == "rfid":
        subtype = first(pairs, "Key type")
        identifier = first(pairs, "Data")
    elif category == "ibutton":
        subtype = first(pairs, "Protocol") or first(pairs, "Key type")
        identifier = first(pairs, "Data")
    elif category == "infrared":
        names = all_values(pairs, "name")
        protocols = all_values(pairs, "protocol")
        subtype = protocols[0] if protocols else None
        extra["signal_count"] = len(names)
        extra["signals"] = names

    return subtype, identifier, frequency, extra


def parse_text(category: str, text: str) -> Tuple[str, Optional[str], Optional[str], Optional[int], dict]:
    """Parse the textual body of a Flipper file.

    Returns ``(filetype, subtype, identifier, frequency, metadata)``. Kept
    separate from :func:`parse_file` so it can be unit-tested without touching
    the filesystem.
    """
    pairs = parse_kv_pairs(text)
    filetype = first(pairs, "Filetype", "") or ""
    subtype, identifier, frequency, extra = _extract(category, pairs)

    metadata: dict = {}
    for key, value in pairs:
        metadata.setdefault(key, value)  # first occurrence wins
    metadata.update(extra)

    return filetype, subtype, identifier, frequency, metadata


def parse_file(path: PathLike) -> FlipperRecord:
    """Parse a single Flipper file into a :class:`FlipperRecord`."""
    p = Path(path)
    data = p.read_bytes()
    sha256 = hashlib.sha256(data).hexdigest()
    category = EXT_CATEGORY.get(p.suffix.lower(), "other")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = ""

    filetype, subtype, identifier, frequency, metadata = parse_text(category, text)

    return FlipperRecord(
        path=str(p),
        filename=p.name,
        category=category,
        filetype=filetype,
        subtype=subtype,
        frequency=frequency,
        identifier=identifier,
        size=len(data),
        sha256=sha256,
        metadata=metadata,
    )


def iter_files(root: PathLike, recursive: bool = True) -> Iterator[Path]:
    """Yield files under ``root`` (or ``root`` itself if it is a file)."""
    p = Path(root)
    if p.is_file():
        yield p
        return
    glob = p.rglob("*") if recursive else p.glob("*")
    for f in sorted(glob):
        if f.is_file():
            yield f


def parse_path(
    root: PathLike,
    recursive: bool = True,
    include_unknown: bool = False,
) -> List[FlipperRecord]:
    """Parse every recognized Flipper file under ``root``.

    Files with an unknown extension are skipped unless ``include_unknown`` is
    set. Individual parse errors are swallowed so one bad file never aborts a
    whole backup scan.
    """
    records: List[FlipperRecord] = []
    for f in iter_files(root, recursive):
        known = f.suffix.lower() in EXT_CATEGORY
        if not known and not include_unknown:
            continue
        try:
            records.append(parse_file(f))
        except OSError:
            continue
    return records
