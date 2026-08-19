"""mevzuat.gov.tr konsolide metin erişimi ve PDF metin çıkarımı.

SOURCE_POLICY.txt bölüm 2 gereği: ingestion için BİRİNCİL kaynak
mevzuat.gov.tr'nin konsolide ("tek metin") PDF/DOC halidir. Bu modül
yalnızca VERİ ÇEKER VE METNE ÇEVİRİR - hiçbir normatif yorum, chunking
veya veritabanına yazma işlemi burada YAPILMAZ (tek sorumluluk ilkesi;
chunking RAG_DESIGN.txt bölüm 4'e göre ayrı bir modülün işi olacak).
"""

from __future__ import annotations

from dataclasses import dataclass

import pymupdf
import pymupdf as fitz

from .http_client import build_session

BASE_URL = "https://www.mevzuat.gov.tr"


@dataclass(frozen=True)
class FetchedDocument:
    mevzuat_kodu: str
    source_url: str
    content_type: str
    raw_bytes: bytes


def document_pdf_url(mevzuat_kodu: str, mevzuat_tipi: str = "yonetmelik") -> str:
    """mevzuat_kodu örneği: '7.5.24408' (Otopark Yönetmeliği).
    Bu kod, mevzuat.gov.tr'nin `?MevzuatNo=...&MevzuatTur=...` sorgu
    sayfasındaki indirme bağlantılarından elde edilir (bkz.
    SOURCE_MAP.txt) - burada TAHMİN EDİLMEZ, çağıran taraf sağlamalı."""

    return f"{BASE_URL}/MevzuatMetin/{mevzuat_tipi}/{mevzuat_kodu}.pdf"


def fetch_consolidated_pdf(mevzuat_kodu: str, mevzuat_tipi: str = "yonetmelik") -> FetchedDocument:
    url = document_pdf_url(mevzuat_kodu, mevzuat_tipi)
    session = build_session()
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return FetchedDocument(
        mevzuat_kodu=mevzuat_kodu,
        source_url=url,
        content_type=response.headers.get("Content-Type", ""),
        raw_bytes=response.content,
    )


def extract_text_by_page(pdf_bytes: bytes) -> list[str]:
    """Native PDF metin katmanından sayfa sayfa metin çıkarır (OCR
    YOK - ARCHITECTURE.txt bölüm 3: OCR yalnızca taranmış belgeler
    için, varsayılan kapalı)."""

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        return [page.get_text() for page in doc]
    finally:
        doc.close()


def has_native_text_layer(pdf_bytes: bytes, min_chars_per_page: int = 50) -> bool:
    """Bir PDF'in gercekten native metin katmani mi tasidigini, yoksa
    taranmis/goruntu tabanli mi oldugunu kabaca ayirt eder. False ise
    OCR gerekebilir (bu modulde implement EDILMEDI - ARCHITECTURE.txt
    bolum 3'teki kasitli kapsam disi karari)."""

    pages = extract_text_by_page(pdf_bytes)
    if not pages:
        return False
    non_trivial_pages = sum(1 for p in pages if len(p.strip()) >= min_chars_per_page)
    return non_trivial_pages / len(pages) >= 0.8
