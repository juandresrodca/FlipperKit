from pathlib import Path

from flipperkit import db, parsers, report

FIXTURES = Path(__file__).parent / "fixtures"


def test_index_and_dedup(tmp_path):
    records = parsers.parse_path(FIXTURES)
    conn = db.connect(tmp_path / "index.db")

    first = db.index_records(conn, records)
    assert first["inserted"] == len(records)
    assert first["updated"] == 0

    # Re-indexing identical content must update, not duplicate.
    second = db.index_records(conn, records)
    assert second["inserted"] == 0
    assert second["updated"] == len(records)

    totals = db.stats(conn)
    assert totals["total"] == len(records)
    conn.close()


def test_load_records_filters(tmp_path):
    conn = db.connect(tmp_path / "index.db")
    db.index_records(conn, parsers.parse_path(FIXTURES))

    nfc = db.load_records(conn, category="nfc")
    assert nfc and all(r.category == "nfc" for r in nfc)

    hits = db.load_records(conn, search="Princeton")
    assert any(r.subtype == "Princeton" for r in hits)
    conn.close()


def test_report_roundtrip_from_db(tmp_path):
    conn = db.connect(tmp_path / "index.db")
    db.index_records(conn, parsers.parse_path(FIXTURES))
    records = db.load_records(conn)
    conn.close()

    html = report.render(records, "html")
    assert "FlipperKit Report" in html
    assert "433.92000 MHz" in html

    md = report.render(records, "md")
    assert "| Category |" in md

    import json

    payload = json.loads(report.render(records, "json"))
    assert payload["summary"]["total"] == len(records)
