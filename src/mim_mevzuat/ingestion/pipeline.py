"""Ingestion Pipeline - Mevzuat belgelerini parse edip SQLite veritabanına
ve FTS5 indeksine aktaran boru hattı.

DATA_MODEL.txt ve ARCHITECTURE.txt ilkelerine uygun olarak:
- Document ve Article kayıtlarını oluşturur.
- Article eklenince SQLite FTS5 indeksi otomatik güncellenir.
- Versiyonlama ve kaynak meta verilerini (source_url, version, jurisdiction)
  tüm maddelere taşır.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..db import connect
from .mevzuat_gov_tr import extract_text_by_page, fetch_consolidated_pdf
from .parser import ParsedDocument, parse_legislation_text


@dataclass
class DocumentMetadata:
    document_id: str
    title: str
    authority: str
    document_type: str
    jurisdiction: str
    publication_date: str
    effective_date: str
    version: str
    source_url: str
    official_source_tier: int = 1
    validity_status: str = "ACTIVE"
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    topics: list[str] = None


@dataclass
class IngestionResult:
    document_id: str
    title: str
    articles_count: int
    topics: list[str]


def ingest_parsed_document(
    conn: sqlite3.Connection,
    meta: DocumentMetadata,
    parsed: ParsedDocument,
) -> IngestionResult:
    """Ayrıştırılmış bir dokümanı ve maddelerini veritabanına kaydeder."""

    now_iso = datetime.now(timezone.utc).isoformat()
    all_topics = set(meta.topics or [])
    for a in parsed.articles:
        all_topics.update(a.topics)
    topics_json = json.dumps(sorted(list(all_topics)), ensure_ascii=False)

    # 1. Document tablosuna yazma (varsa güncelle)
    conn.execute(
        """
        INSERT INTO document (
            document_id, title, authority, document_type, jurisdiction,
            publication_date, effective_date, last_amended_date, version,
            source_url, official_source_tier, retrieved_at, validity_status,
            supersedes, superseded_by, topics
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            title=excluded.title,
            authority=excluded.authority,
            document_type=excluded.document_type,
            jurisdiction=excluded.jurisdiction,
            publication_date=excluded.publication_date,
            effective_date=excluded.effective_date,
            last_amended_date=excluded.last_amended_date,
            version=excluded.version,
            source_url=excluded.source_url,
            official_source_tier=excluded.official_source_tier,
            retrieved_at=excluded.retrieved_at,
            validity_status=excluded.validity_status,
            supersedes=excluded.supersedes,
            superseded_by=excluded.superseded_by,
            topics=excluded.topics
        """,
        (
            meta.document_id,
            meta.title or parsed.title,
            meta.authority,
            meta.document_type,
            meta.jurisdiction,
            meta.publication_date,
            meta.effective_date,
            meta.publication_date,
            meta.version,
            meta.source_url,
            meta.official_source_tier,
            now_iso,
            meta.validity_status,
            meta.supersedes,
            meta.superseded_by,
            topics_json,
        ),
    )

    # 2. Önceki article kayıtlarını temizle (idempotency)
    conn.execute("DELETE FROM article WHERE document_id = ?", (meta.document_id,))

    # 3. Maddeleri ekle
    for idx, art in enumerate(parsed.articles):
        # Format: doc_id:madde_X[:fikra_Y]
        p_part = f":f{art.paragraph}" if art.paragraph else ""
        sp_part = f":b{art.subparagraph}" if art.subparagraph else ""
        art_num_clean = art.article.lower().replace(" ", "_").replace(".", "")
        article_id = f"{meta.document_id}:{art_num_clean}{p_part}{sp_part}"
        if len(parsed.articles) > 1:
            article_id += f":{idx}"

        art_topics_json = json.dumps(art.topics, ensure_ascii=False)

        conn.execute(
            """
            INSERT INTO article (
                article_id, document_id, article, paragraph, subparagraph,
                text, effective_from, effective_to, jurisdiction, topics
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                article_id,
                meta.document_id,
                art.article,
                art.paragraph,
                art.subparagraph,
                art.text,
                meta.effective_date,
                None,
                meta.jurisdiction,
                art_topics_json,
            ),
        )

    conn.commit()
    return IngestionResult(
        document_id=meta.document_id,
        title=meta.title or parsed.title,
        articles_count=len(parsed.articles),
        topics=sorted(list(all_topics)),
    )


def ingest_text(
    conn: sqlite3.Connection,
    meta: DocumentMetadata,
    raw_text: str,
) -> IngestionResult:
    """Ham metin halindeki bir mevzuat belgesini parse edip veritabanına aktarır."""
    parsed = parse_legislation_text(raw_text)
    return ingest_parsed_document(conn, meta, parsed)


def ingest_pdf_bytes(
    conn: sqlite3.Connection,
    meta: DocumentMetadata,
    pdf_bytes: bytes,
) -> IngestionResult:
    """PDF baytlarından metin çıkarıp parse eder ve veritabanına aktarır."""
    pages = extract_text_by_page(pdf_bytes)
    full_text = "\n".join(pages)
    parsed = parse_legislation_text(full_text)
    return ingest_parsed_document(conn, meta, parsed)


def ingest_pdf_file(
    conn: sqlite3.Connection,
    meta: DocumentMetadata,
    pdf_path: str | Path,
) -> IngestionResult:
    """Yerel bir PDF dosyasından mevzuatı sisteme alır."""
    pdf_bytes = Path(pdf_path).read_bytes()
    return ingest_pdf_bytes(conn, meta, pdf_bytes)
