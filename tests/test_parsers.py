from pathlib import Path

import pytest

from flipperkit import parsers

FIXTURES = Path(__file__).parent / "fixtures"


def test_parse_nfc():
    rec = parsers.parse_file(FIXTURES / "sample.nfc")
    assert rec.category == "nfc"
    assert rec.filetype == "Flipper NFC device"
    assert rec.subtype == "Mifare Classic"
    assert rec.identifier == "04 A2 26 B1 5C 3D 80"
    assert rec.frequency is None
    assert len(rec.sha256) == 64
    assert rec.size > 0


def test_parse_subghz():
    rec = parsers.parse_file(FIXTURES / "sample.sub")
    assert rec.category == "subghz"
    assert rec.subtype == "Princeton"
    assert rec.frequency == 433_920_000
    assert rec.identifier == "00 00 00 00 00 12 34 56"
    assert rec.metadata["preset"] == "FuriHalSubGhzPresetOok650Async"


def test_parse_rfid():
    rec = parsers.parse_file(FIXTURES / "sample.rfid")
    assert rec.category == "rfid"
    assert rec.subtype == "EM4100"
    assert rec.identifier == "1A 2B 3C 4D 5E"


def test_parse_infrared_counts_signals():
    rec = parsers.parse_file(FIXTURES / "sample.ir")
    assert rec.category == "infrared"
    assert rec.subtype == "NEC"
    assert rec.metadata["signal_count"] == 2
    assert rec.metadata["signals"] == ["Power", "Vol_up"]


def test_comments_and_blank_lines_are_ignored():
    pairs = parsers.parse_kv_pairs("# comment\n\nKey: Value\n")
    assert pairs == [("Key", "Value")]


def test_parse_path_scans_directory():
    records = parsers.parse_path(FIXTURES)
    categories = {r.category for r in records}
    assert {"nfc", "subghz", "rfid", "infrared"} <= categories
    assert len(records) >= 4


def test_unknown_extension_skipped(tmp_path):
    (tmp_path / "notes.txt").write_text("Filetype: something\n")
    assert parsers.parse_path(tmp_path) == []
    assert len(parsers.parse_path(tmp_path, include_unknown=True)) == 1
