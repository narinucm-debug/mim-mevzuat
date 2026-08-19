"""Test jurisdictions and update engine."""

from mim_mevzuat.jurisdictions import resolve_jurisdiction
from mim_mevzuat.update_engine.diff_engine import compare_documents
from mim_mevzuat.ingestion.parser import parse_legislation_text


def test_jurisdiction_resolution_for_various_districts():
    # İlçe seviyesi
    jur, prov, dist = resolve_jurisdiction("Çankaya Gaziosmanpaşa")
    assert jur == "TR.Ankara.Cankaya"
    assert prov == "Ankara"
    assert dist == "Çankaya"

    # İstanbul Kadıköy
    jur, prov, dist = resolve_jurisdiction("Kadıköy Fikirtepe kentsel dönüşüm")
    assert jur == "TR.Istanbul.Kadikoy"
    assert dist == "Kadıköy"

    # Muğla Bodrum
    jur, prov, dist = resolve_jurisdiction("Bodrum Yalıkavak villa projesi")
    assert jur == "TR.Mugla.Bodrum"

    # Antalya Finike
    jur, prov, dist = resolve_jurisdiction("Finike sahil şeridi")
    assert jur == "TR.Antalya.Finike"

    # Sadece İl
    jur, prov, dist = resolve_jurisdiction("İzmir geneli imar planı")
    assert jur == "TR.Izmir"
    assert dist is None


def test_diff_engine_detects_amended_articles():
    v1_text = """
    PLANLI ALANLAR İMAR YÖNETMELİĞİ
    MADDE 5 – (1) Yapı ruhsatı alınmadan inşaata başlanamaz.
    MADDE 6 – (1) Asansör yapılması 3 katlı binalarda zorunludur.
    """
    v2_text = """
    PLANLI ALANLAR İMAR YÖNETMELİĞİ
    MADDE 5 – (1) Yapı ruhsatı alınmadan inşaata başlanamaz.
    MADDE 6 – (1) Asansör yapılması 4 katlı binalarda zorunludur.
    MADDE 7 – (1) Yeni eklenen hüküm.
    """
    doc1 = parse_legislation_text(v1_text)
    doc2 = parse_legislation_text(v2_text)

    report = compare_documents("Planlı Alanlar", doc1, "2024.01", doc2, "2026.07")

    assert report.changes_count >= 2
    # Madde 6 değişti
    assert any("Madde 6" in m.article for m in report.modified_articles)
    # Madde 7 eklendi
    assert any("Madde 7" in a.article for a in report.added_articles)
