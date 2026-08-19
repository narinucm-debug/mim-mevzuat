"""Retrieval Layer - RAG_DESIGN.txt ve ARCHITECTURE.txt ilkelerine uygun
olarak SQLite FTS5 (BM25) ve metadata filtreleriyle Evidence üretimi.

Özellikler:
- BM25 tam metin araması (SQLite FTS5).
- Türkçe stopword ve terim kapsama (term coverage) filtresi.
- Jurisdiction hiyerarşisi genişletmesi:
  'TR.Ankara.Cankaya' -> ['TR.Ankara.Cankaya', 'TR.Ankara', 'TR']
- Yürürlük tarihi ve belge geçerlilik durumu ('ACTIVE') filtrelemesi.
- Topic / Doküman filtreleme ve alaka skorlama.
- Citation Enforcer ve Answer Composer'ın beklediği Evidence listesi çıktısı.
"""

from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass, field
from typing import Optional

from .db import has_fts5
from .models import Evidence

TURKISH_STOPWORDS = {
    "ve", "veya", "ile", "icin", "için", "bir", "bu", "de", "da", "hangi",
    "nasil", "nasıl", "nedir", "ne", "mi", "mı", "mu", "mü", "olan", "olarak",
    "gore", "göre", "kadar", "dair", "ise", "diye", "gibi", "en", "cok",
    "çok", "az", "tam", "her", "tum", "tüm", "hakkinda", "hakkında", "ilgili",
    "var", "yok", "oldu", "olur", "muyum", "miyim", "musun", "misin", "mı",
    "yapıyorum", "yaptım", "ayırdım", "koydum", "kurtarır", "yeter", "lazım",
    "gerek", "eder", "m2", "adet", "tane", "ben", "sen", "biz", "siz", "m²",
}


@dataclass
class QueryFilter:
    jurisdiction: Optional[str] = None       # ör. "TR.Ankara.Cankaya"
    topics: list[str] = field(default_factory=list)
    document_id: Optional[str] = None
    article: Optional[str] = None
    effective_date: Optional[str] = None     # YYYY-MM-DD
    validity_status: str = "ACTIVE"
    limit: int = 5


def expand_jurisdiction_hierarchy(jurisdiction: str | None) -> list[str]:
    """Jurisdiction hiyerarşisini yukarı doğru genişletir.
    DATA_MODEL.txt bölüm 3:
      'TR.Ankara.Cankaya' -> ['TR.Ankara.Cankaya', 'TR.Ankara', 'TR']
      'TR.Ankara'         -> ['TR.Ankara', 'TR']
      'TR'                -> ['TR']
    """
    if not jurisdiction:
        return ["TR"]

    parts = jurisdiction.strip().split(".")
    expanded: list[str] = []
    for i in range(len(parts), 0, -1):
        expanded.append(".".join(parts[:i]))
    return expanded


def _extract_query_tokens(query: str) -> list[str]:
    """Sorgudan anlamlı anahtar kelimeleri çıkarır."""
    cleaned = re.sub(r'[^\w\sğüşıöçĞÜŞİÖÇ]', ' ', query)
    tokens = [t.strip().lower() for t in cleaned.split() if len(t.strip()) > 1]
    substantive = [t for t in tokens if t not in TURKISH_STOPWORDS]
    return substantive or tokens


def _clean_fts_query(query: str) -> str:
    """Kullanıcı sorgusundan FTS5 uyumlu arama ifadesi türetir."""
    tokens = _extract_query_tokens(query)
    if not tokens:
        return ""

    escaped_tokens = [f'"{t}"*' for t in tokens]
    return " OR ".join(escaped_tokens)


class RetrievalEngine:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        # FTS5'in bu SQLite derlemesinde mevcut olup olmadığı BİR KERE
        # tespit edilir (ör. Chaquopy/Android'de FTS5 modülü YOK - bkz.
        # db.py). Yoksa aşağıdaki basit filtre + terim eşleştirme
        # yoluna düşülür; sistem çökmez, yalnızca sıralama BM25 yerine
        # basit terim kapsama sayısına dayanır.
        self.fts_available = has_fts5(conn)

    def retrieve(
        self,
        query: str,
        filters: Optional[QueryFilter] = None,
    ) -> list[Evidence]:
        """Kullanıcı sorgusunu ve filtreleri kullanarak kanıt (Evidence)
        parçacıklarını çeker."""

        if filters is None:
            filters = QueryFilter()

        # 1. Belirli bir madde numarası sorulmuş mu kontrol et (ör. "madde 47")
        asked_article_match = re.search(r"(?:madde|m)\s*(\d+)", query, re.IGNORECASE)
        specific_article_target = None
        if asked_article_match and not filters.article:
            specific_article_target = f"Madde {asked_article_match.group(1)}"

        # 2. Jurisdiction listesi
        jurisdictions = expand_jurisdiction_hierarchy(filters.jurisdiction)
        jur_placeholders = ",".join("?" for _ in jurisdictions)

        fts_query = _clean_fts_query(query)
        substantive_tokens = _extract_query_tokens(query)

        params: list[any] = []

        use_fts = self.fts_available and bool(fts_query)

        if use_fts:
            sql = f"""
            SELECT
                a.article_id,
                a.document_id,
                a.article,
                a.paragraph,
                a.subparagraph,
                a.text,
                a.jurisdiction,
                d.source_url,
                d.version,
                d.validity_status,
                d.topics as doc_topics,
                bm25(article_fts) as rank_score
            FROM article_fts
            JOIN article a ON a.article_id = article_fts.article_id
            JOIN document d ON d.document_id = a.document_id
            WHERE article_fts MATCH ?
              AND a.jurisdiction IN ({jur_placeholders})
            """
            params.append(fts_query)
            params.extend(jurisdictions)
        else:
            sql = f"""
            SELECT
                a.article_id,
                a.document_id,
                a.article,
                a.paragraph,
                a.subparagraph,
                a.text,
                a.jurisdiction,
                d.source_url,
                d.version,
                d.validity_status,
                d.topics as doc_topics,
                0.0 as rank_score
            FROM article a
            JOIN document d ON d.document_id = a.document_id
            WHERE a.jurisdiction IN ({jur_placeholders})
            """
            params.extend(jurisdictions)

        # Geçerlilik durumu filtresi
        if filters.validity_status:
            sql += " AND d.validity_status = ?"
            params.append(filters.validity_status)

        # Doküman filtresi
        if filters.document_id:
            sql += " AND a.document_id = ?"
            params.append(filters.document_id)

        # Madde numarası filtresi
        target_art = filters.article or specific_article_target
        if target_art:
            sql += " AND LOWER(a.article) = LOWER(?)"
            params.append(target_art.strip())

        # Sıralama: BM25 skoru (FTS5'te küçük/negatif değerler daha iyi eşleşmedir)
        if use_fts:
            sql += " ORDER BY rank_score ASC"
        else:
            sql += " ORDER BY a.article_id ASC"

        if use_fts:
            sql += f" LIMIT {filters.limit * 2}"  # Post-filter için biraz fazla çek
        # FTS5 yoksa LIMIT SQL seviyesinde uygulanmaz: article_id sırasına
        # göre kesip alakalı maddeleri kaçırmamak için tüm adaylar Python
        # tarafında puanlanıp sıralanır (küçük corpus'ta bu ucuzdur).

        cursor = self.conn.cursor()
        try:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            return []

        # Eğer belirli bir madde hedeflenmiş ve bulunamadıysa (ör. Madde 47) boş dön
        if specific_article_target and not rows:
            return []

        scored: list[tuple[float, Evidence]] = []
        for r in rows:
            text_low = r["text"].lower()
            art_low = r["article"].lower()
            matched_count = 0

            # Term coverage kontrolü:
            # Çok kelimeli sorgularda en az bir anahtar kelimenin gerçekten metinde
            # geçmesi gerekir (sadece rastgele bir harf veya alakasız kelime eşleşmesini önler)
            if substantive_tokens and not target_art:
                matched_count = sum(1 for token in substantive_tokens if token in text_low or token in art_low)
                if matched_count == 0:
                    continue
                # Eğer sorguda 3+ anlamlı kelime varsa ve sadece 1 çok genel kelime geçiyorsa
                # ve hiçbir özel terim yoksa ele
                if len(substantive_tokens) >= 3 and matched_count < 2:
                    # Özel terimler (otopark, emsal, kaks, taks, yangın, sığınak, asansör) var mı?
                    has_core = any(
                        t in ["otopark", "emsal", "kaks", "taks", "yangın", "yangin", "sığınak", "siginak", "asansör", "asansor"]
                        for t in substantive_tokens if t in text_low
                    )
                    if not has_core:
                        continue

            score = float(r["rank_score"]) if "rank_score" in r.keys() else 0.0
            evidence = Evidence(
                document_id=r["document_id"],
                article=r["article"],
                paragraph=r["paragraph"],
                subparagraph=r["subparagraph"],
                text=r["text"],
                source_url=r["source_url"],
                version=r["version"],
                jurisdiction=r["jurisdiction"],
                retrieval_score=score,
            )
            # FTS yokken siralama anahtari: daha fazla eslesen terim once gelsin
            # (SQL'deki bm25 ASC sirasinin yerini tutar - kucuk = iyi, o yuzden negatif).
            sort_key = score if use_fts else -matched_count
            scored.append((sort_key, evidence))
            if use_fts and len(scored) >= filters.limit:
                break

        if not use_fts:
            scored.sort(key=lambda pair: pair[0])

        return [evidence for _, evidence in scored[: filters.limit]]
