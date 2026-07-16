"""SQLite index for parsed Flipper records.

Content is deduplicated by SHA-256: re-indexing the same artifact updates its
``last_seen`` timestamp and path instead of creating a duplicate row.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional, Union

from .models import FlipperRecord

PathLike = Union[str, Path]

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    sha256      TEXT PRIMARY KEY,
    path        TEXT NOT NULL,
    filename    TEXT NOT NULL,
    category    TEXT NOT NULL,
    filetype    TEXT,
    subtype     TEXT,
    frequency   INTEGER,
    identifier  TEXT,
    size        INTEGER,
    metadata    TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_records_category ON records(category);
CREATE INDEX IF NOT EXISTS idx_records_subtype  ON records(subtype);
"""


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db_path: PathLike) -> sqlite3.Connection:
    """Open (creating if needed) the index database."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def upsert(conn: sqlite3.Connection, record: FlipperRecord) -> bool:
    """Insert ``record`` or refresh an existing row with the same SHA-256.

    Returns ``True`` if a new row was inserted, ``False`` if an existing one
    was updated.
    """
    now = _utcnow()
    cur = conn.execute("SELECT sha256 FROM records WHERE sha256 = ?", (record.sha256,))
    exists = cur.fetchone() is not None
    if exists:
        conn.execute(
            "UPDATE records SET path = ?, filename = ?, last_seen = ? WHERE sha256 = ?",
            (record.path, record.filename, now, record.sha256),
        )
    else:
        conn.execute(
            """
            INSERT INTO records (
                sha256, path, filename, category, filetype, subtype,
                frequency, identifier, size, metadata, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.sha256,
                record.path,
                record.filename,
                record.category,
                record.filetype,
                record.subtype,
                record.frequency,
                record.identifier,
                record.size,
                json.dumps(record.metadata),
                now,
                now,
            ),
        )
    return not exists


def index_records(conn: sqlite3.Connection, records: Iterable[FlipperRecord]) -> dict:
    """Upsert many records in one transaction. Returns insert/update counts."""
    inserted = updated = 0
    with conn:
        for record in records:
            if upsert(conn, record):
                inserted += 1
            else:
                updated += 1
    return {"inserted": inserted, "updated": updated}


def _row_to_record(row: sqlite3.Row) -> FlipperRecord:
    return FlipperRecord(
        path=row["path"],
        filename=row["filename"],
        category=row["category"],
        filetype=row["filetype"] or "",
        subtype=row["subtype"],
        frequency=row["frequency"],
        identifier=row["identifier"],
        size=row["size"] or 0,
        sha256=row["sha256"],
        metadata=json.loads(row["metadata"]) if row["metadata"] else {},
    )


def load_records(
    conn: sqlite3.Connection,
    category: Optional[str] = None,
    search: Optional[str] = None,
) -> List[FlipperRecord]:
    """Load records, optionally filtered by category and/or a text search."""
    query = "SELECT * FROM records"
    clauses: List[str] = []
    params: List[object] = []
    if category:
        clauses.append("category = ?")
        params.append(category)
    if search:
        clauses.append("(filename LIKE ? OR identifier LIKE ? OR subtype LIKE ?)")
        needle = f"%{search}%"
        params.extend([needle, needle, needle])
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY category, subtype, filename"
    rows = conn.execute(query, params).fetchall()
    return [_row_to_record(r) for r in rows]


def stats(conn: sqlite3.Connection) -> dict:
    """Summary counts for the whole index."""
    total = conn.execute("SELECT COUNT(*) AS n, COALESCE(SUM(size), 0) AS b FROM records").fetchone()
    by_category = conn.execute(
        "SELECT category, COUNT(*) AS n FROM records GROUP BY category ORDER BY n DESC"
    ).fetchall()
    return {
        "total": total["n"],
        "total_bytes": total["b"],
        "by_category": {r["category"]: r["n"] for r in by_category},
    }
