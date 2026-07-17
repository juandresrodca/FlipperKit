"""Flipper port detection is tested with fake pyserial port objects."""

from types import SimpleNamespace

from flipperkit.client import FLIPPER_PID, FLIPPER_VID, is_flipper_port


def _port(**kwargs):
    base = {"device": "COM3", "description": "", "vid": None, "pid": None,
            "manufacturer": None, "product": None}
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_detects_by_vid_pid():
    assert is_flipper_port(_port(vid=FLIPPER_VID, pid=FLIPPER_PID)) is True


def test_detects_by_stm_description():
    port = _port(description="STMicroelectronics Virtual COM Port (COM7)")
    assert is_flipper_port(port) is True


def test_detects_by_flipper_manufacturer():
    assert is_flipper_port(_port(manufacturer="Flipper Devices Inc.")) is True


def test_ignores_unrelated_port():
    port = _port(description="Standard Serial over Bluetooth link (COM5)")
    assert is_flipper_port(port) is False


def test_wrong_vid_pid_without_hint_is_not_flipper():
    assert is_flipper_port(_port(vid=0x1234, pid=0x5678)) is False
