"""Retrieval testleri - BM25 tam metin araması, jurisdiction hiyerarşisi
ve filtreleri test eder."""

from pathlib import Path
import pytest

from mim_mevzuat.db import apply_schema, connect
from mim_mevzuat.ingestion.pipeline import DocumentMetadata, ingest_pdf_file, ingest_text
from mim_mevzuat.retrieval import QueryFilter, RetrievalEngine, expand_jurisdiction_hierarchy

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "otopark_yonetmeligi_sample.pdf"


@pytest.fixture
def test_db():
    conn = connect(":memory:")
    apply_schema(conn)

    # 1. Otopark Yönetmeliği (TR ulusal)
    meta_otopark = DocumentMetadata(
        document_id="yonetmelik:7.5.24408",
        title="Otopark Yönetmeliği",
        authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
        document_type="yonetmelik",
        jurisdiction="TR",
        publication_date="2018-02-22",
        effective_date="2018-06-01",
        version="2022.06",
        source_url="https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.24408.pdf",
        validity_status="ACTIVE",
    )
    ingest_pdf_file(conn, meta_otopark, FIXTURE_PDF)

    # 2. Planlı Alanlar İmar Yönetmeliği örnek metni (TR ulusal)
    planli_alanlar_sample = """
    PLANLI ALANLAR İMAR YÖNETMELİĞİ

    MADDE 5 – (1) İmar planlarında su taşkın alanı olarak belirlenen yerlerde yapı yapılamaz.
    (2) Yapı ruhsatı alınmadan hiçbir yapının inşasına başlanamaz.
    (3) Emsal hesabı (KAKS), parsel alanının net imar parseli alanı üzerinden hesaplanan ve yapı inşaat alanını belirleyen katsayıdır.

    MADDE 22 – (1) Emsal hesabına dahil edilmeyecek alanlar:
    a) Tamamen toprağın altında kalan bodrum katlardaki otoparklar,
    b) Sığınak, yangın merdiveni ve asansör boşlukları emsale dahil edilmez.
    """
    meta_planli = DocumentMetadata(
        document_id="yonetmelik:7.5.23722",
        title="Planlı Alanlar İmar Yönetmeliği",
        authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
        document_type="yonetmelik",
        jurisdiction="TR",
        publication_date="2017-07-03",
        effective_date="2017-10-01",
        version="2026.07",
        source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=23722&MevzuatTur=7&MevzuatTertip=5",
        validity_status="ACTIVE",
    )
    ingest_text(conn, meta_planli, planli_alanlar_sample)

    yield conn
    conn.close()


def test_jurisdiction_expansion():
    assert expand_jurisdiction_hierarchy("TR.Ankara.Cankaya") == [
        "TR.Ankara.Cankaya",
        "TR.Ankara",
        "TR",
    ]
    assert expand_jurisdiction_hierarchy("TR.Ankara") == ["TR.Ankara", "TR"]
    assert expand_jurisdiction_hierarchy("TR") == ["TR"]
    assert expand_jurisdiction_hierarchy(None) == ["TR"]


def test_retrieve_otopark_general_principles(test_db):
    engine = RetrievalEngine(test_db)
    results = engine.retrieve("otopark ihtiyacının parselinde karşılanması")

    assert len(results) > 0
    # Otopark Yönetmeliği'nden gelmeli
    top = results[0]
    assert top.document_id == "yonetmelik:7.5.24408"
    assert "otopark" in top.text.lower()
    assert top.source_url.startswith("https://www.mevzuat.gov.tr")
    assert top.version == "2022.06"


def test_retrieve_emsal_and_kaks(test_db):
    engine = RetrievalEngine(test_db)
    results = engine.retrieve("emsal hesabı dahil edilmeyecek alanlar")

    assert len(results) > 0
    top = results[0]
    assert top.document_id == "yonetmelik:7.5.23722"
    assert "emsal" in top.text.lower()


def test_retrieve_with_jurisdiction_filtering(test_db):
    engine = RetrievalEngine(test_db)
    # Çankaya sorgusu ulusal TR hükümlerini de getirmeli
    results = engine.retrieve(
        "otopark",
        QueryFilter(jurisdiction="TR.Ankara.Cankaya", limit=3),
    )
    assert len(results) > 0
    assert all(r.jurisdiction in ["TR", "TR.Ankara", "TR.Ankara.Cankaya"] for r in results)


def test_retrieve_nonexistent_topic_returns_empty(test_db):
    engine = RetrievalEngine(test_db)
    results = engine.retrieve("kuantum lazer silahı füzyon reaktörü")
    assert len(results) == 0
