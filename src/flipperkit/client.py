"""Serial client for the Flipper Zero CLI.

The Flipper exposes a text CLI over its USB CDC serial port. Every response is
terminated by the ``>: `` prompt, which this client reads up to. Only the
subset of commands FlipperKit needs (device info, directory listing, file read)
is wrapped here.

This module is intentionally the only place that imports :mod:`serial`, so the
rest of the toolkit stays testable without hardware. See
:class:`flipperkit.backup.RemoteFS` for the protocol the backup logic depends
on — any object implementing it (including a fake) works.
"""

from __future__ import annotations

import time
from typing import List, Optional, Tuple

try:  # pyserial is optional at import time; only needed for real devices.
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - exercised only without pyserial
    serial = None
    list_ports = None

PROMPT = b">: "

# The Flipper Zero enumerates as an STMicroelectronics Virtual COM Port.
FLIPPER_VID = 0x0483
FLIPPER_PID = 0x5740
FLIPPER_DESC_HINTS = ("flipper", "stmicroelectronics")


class FlipperError(RuntimeError):
    """Raised when the device is unreachable or returns an error."""


def is_flipper_port(port) -> bool:
    """Heuristically decide whether a pyserial port is a Flipper Zero.

    Matches on the STM32 USB VID/PID first (most reliable), then falls back to
    the port description / manufacturer text, which on Windows reads
    "STMicroelectronics Virtual COM Port".
    """
    if getattr(port, "vid", None) == FLIPPER_VID and getattr(port, "pid", None) == FLIPPER_PID:
        return True
    haystack = " ".join(
        filter(None, (port.description, getattr(port, "manufacturer", None), getattr(port, "product", None)))
    ).lower()
    return any(hint in haystack for hint in FLIPPER_DESC_HINTS)


def available_ports() -> List[Tuple[str, str, bool]]:
    """Return ``(device, description, is_flipper)`` for each serial port."""
    if list_ports is None:
        raise FlipperError("pyserial is not installed; run `pip install pyserial`.")
    return [(p.device, p.description, is_flipper_port(p)) for p in list_ports.comports()]


class FlipperClient:
    """A thin wrapper over the Flipper Zero serial CLI."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 2.0):
        if serial is None:
            raise FlipperError("pyserial is not installed; run `pip install pyserial`.")
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial: Optional["serial.Serial"] = None

    # -- lifecycle ---------------------------------------------------------
    def open(self) -> "FlipperClient":
        try:
            self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
        except serial.SerialException as exc:  # type: ignore[union-attr]
            raise FlipperError(f"Could not open {self.port}: {exc}") from exc
        time.sleep(0.2)
        self._read_until_prompt()  # consume the banner
        return self

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
            self._serial = None

    def __enter__(self) -> "FlipperClient":
        return self.open()

    def __exit__(self, *exc) -> None:
        self.close()

    # -- low level ---------------------------------------------------------
    def _read_until_prompt(self) -> bytes:
        assert self._serial is not None
        buffer = bytearray()
        deadline = time.time() + max(self.timeout, 5.0)
        while time.time() < deadline:
            chunk = self._serial.read(256)
            if chunk:
                buffer.extend(chunk)
                if buffer.endswith(PROMPT):
                    break
            elif buffer:
                break
        return bytes(buffer)

    def command(self, cmd: str) -> str:
        """Send one CLI command and return its textual response."""
        if self._serial is None:
            raise FlipperError("Client is not open; call open() first.")
        self._serial.reset_input_buffer()
        self._serial.write(cmd.encode() + b"\r\n")
        raw = self._read_until_prompt()
        return _clean_response(raw, cmd)

    # -- high level --------------------------------------------------------
    def device_info(self) -> dict:
        """Parse the ``device_info`` command into a dict."""
        text = self.command("device_info")
        info: dict = {}
        for line in text.splitlines():
            key, sep, value = line.partition(":")
            if sep:
                info[key.strip()] = value.strip()
        return info

    def list_dir(self, path: str) -> List[Tuple[str, bool, int]]:
        """List one directory. Returns ``(name, is_dir, size)`` tuples.

        Flipper prints ``[D] name`` for directories and ``[F] name size`` for
        files.
        """
        text = self.command(f"storage list {path}")
        entries: List[Tuple[str, bool, int]] = []
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("[D]"):
                entries.append((line[3:].strip(), True, 0))
            elif line.startswith("[F]"):
                body = line[3:].strip()
                name, _, size = body.rpartition(" ")
                if name and size.isdigit():
                    entries.append((name, False, int(size)))
                else:
                    entries.append((body, False, 0))
        return entries

    def read_file(self, path: str) -> bytes:
        """Read a file over the CLI.

        Note: ``storage read`` streams the file body after a ``Size: N`` line.
        This is reliable for the UTF-8 text artifacts FlipperKit parses; truly
        binary blobs may need ``storage read_chunks`` (future work).
        """
        text = self.command(f"storage read {path}")
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("Size:"):
            lines = lines[1:]
        return "\n".join(lines).encode()


def _clean_response(raw: bytes, cmd: str) -> str:
    """Strip the echoed command and trailing prompt from a raw response."""
    text = raw.decode(errors="replace")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if text.endswith(">: "):
        text = text[: -len(">: ")]
    lines = text.split("\n")
    if lines and lines[0].strip() == cmd.strip():
        lines = lines[1:]
    return "\n".join(lines).strip("\n")
