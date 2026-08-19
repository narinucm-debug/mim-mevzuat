"""Ince bir SQLite yardimci katmani - ORM yok, ham SQL. sqlite3 stdlib
FTS5'i destekliyorsa (python.org derlemeleri destekler) schema.sql
sorunsuz uygulanir. FTS5 modulu bulunmayan SQLite derlemelerinde
(ör. Chaquopy/Android - bkz. schema_fts5.sql) uygulama CALISMAYA DEVAM
EDER, yalnizca RetrievalEngine FTS5'siz moda gecer."""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_PATH = Path(__file__).parent / "schema.sql"
SCHEMA_FTS5_PATH = Path(__file__).parent / "schema_fts5.sql"


def connect(db_path: str | Path, check_same_thread: bool = False) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=check_same_thread)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()

    # FTS5 best-effort: bazı SQLite derlemelerinde (ör. Chaquopy/Android)
    # FTS5 modulu YOKTUR - bu durumda "no such module: fts5" hatasi
    # ATLANIR, temel sema zaten uygulanmis oldugundan sistem calismaya
    # devam eder (bkz. RAPOR/retrieval.py fallback).
    try:
        conn.executescript(SCHEMA_FTS5_PATH.read_text(encoding="utf-8"))
        conn.commit()
    except sqlite3.OperationalError:
        pass


def has_fts5(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='article_fts'"
    ).fetchone()
    return row is not None
