"""Data models shared across FlipperKit."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class FlipperRecord:
    """A normalized description of one artifact captured by a Flipper Zero.

    A record is derived from a single file on the device's SD card. The
    ``category`` is a coarse bucket (``nfc``, ``subghz``, ``rfid`` …) while
    ``subtype`` holds the finer-grained protocol or chip family reported inside
    the file itself.
    """

    path: str
    filename: str
    category: str
    filetype: str
    subtype: Optional[str] = None
    frequency: Optional[int] = None
    identifier: Optional[str] = None
    size: int = 0
    sha256: str = ""
    metadata: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)
