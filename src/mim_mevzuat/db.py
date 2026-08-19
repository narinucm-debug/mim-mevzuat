"""Ince bir SQLite yardimci katmani - ORM yok, ham SQL. sqlite3 stdlib
FTS5'i destekliyorsa (python.org derlemeleri destekler) schema.sql
sorunsuz uygulanir."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def connect(db_path: str | Path, check_same_thread: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()
