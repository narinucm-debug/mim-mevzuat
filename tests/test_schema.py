"""Şema testleri: DATA_MODEL.txt'teki alanların gerçekten uygulanabilir
olduğunu ve FTS5 tam metin aramasının çalıştığını doğrular."""

import sqlite3

import pytest

from mim_mevzuat.db import apply_schema, connect


@pytest.fixture()
def db(tmp_path):
    conn = connect(tmp_path / "test.db")
    apply_schema(conn)
    yield conn
    conn.close()


def test_schema_applies_without_error(db):
    tables = {
        row["name"]
        for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert {"document", "article", "project", "rule_pack", "calculation_trace", "answer"} <= tables


def test_document_and_article_insert_and_fts_search(db):
    db.execute(
        """
        INSERT INTO document (
            document_id, title, authority, document_type, jurisdiction,
            publication_date, effective_date, last_amended_date, version,
            source_url, official_source_tier, retrieved_at, validity_status,
            topics
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "otopark-yonetmeligi",
            "Otopark Yönetmeliği",
            "Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            "yonetmelik",
            "TR",
            "1993-07-31",
            "1993-07-31",
            "2026-01-01",
            "2026.01",
            "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=24408&MevzuatTur=7&MevzuatTertip=5",
            2,
            "2026-08-19",
            "ACTIVE",
            '["otopark", "ev-sarj"]',
        ),
    )
    db.execute(
        """
        INSERT INTO article (
            article_id, document_id, article, paragraph, text,
            jurisdiction, topics
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "otopark-yonetmeligi:5:1",
            "otopark-yonetmeligi",
            "5",
            "1",
            "Yapılacak binalarda otopark ihtiyacının bina içinde veya "
            "parselinde karşılanması esastır.",
            "TR",
            '["otopark"]',
        ),
    )
    db.commit()

    rows = db.execute(
        "SELECT article_id FROM article_fts WHERE article_fts MATCH ?",
        ("otopark",),
    ).fetchall()

    assert [r["article_id"] for r in rows] == ["otopark-yonetmeligi:5:1"]


def test_article_fts_stays_in_sync_after_delete(db):
    db.execute(
        """
        INSERT INTO document (
            document_id, title, document_type, jurisdiction, version,
            source_url, official_source_tier, retrieved_at, validity_status
        ) VALUES ('d1', 't', 'yonetmelik', 'TR', '1', 'https://x', 2, '2026-08-19', 'ACTIVE')
        """
    )
    db.execute(
        """
        INSERT INTO article (article_id, document_id, article, text, jurisdiction)
        VALUES ('d1:1', 'd1', '1', 'sığınak hesabı örnek metin', 'TR')
        """
    )
    db.commit()

    db.execute("DELETE FROM article WHERE article_id = 'd1:1'")
    db.commit()

    rows = db.execute(
        "SELECT * FROM article_fts WHERE article_fts MATCH 'sığınak'"
    ).fetchall()
    assert rows == []


def test_invalid_validity_status_rejected(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            """
            INSERT INTO document (
                document_id, title, document_type, jurisdiction, version,
                source_url, official_source_tier, retrieved_at, validity_status
            ) VALUES ('d2', 't', 'yonetmelik', 'TR', '1', 'https://x', 2, '2026-08-19', 'GECERSIZ')
            """
        )
