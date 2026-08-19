"""Parser unit testleri - Madde, fıkra ve değişiklik işaretlerinin
doğru ayrıştırıldığını doğrular."""

from pathlib import Path

from mim_mevzuat.ingestion.mevzuat_gov_tr import extract_text_by_page
from mim_mevzuat.ingestion.parser import parse_legislation_text

FIXTURE_PDF = Path(__file__).parent / "fixtures" / "otopark_yonetmeligi_sample.pdf"


def test_parse_sample_pdf_fixture():
    pages = extract_text_by_page(FIXTURE_PDF.read_bytes())
    full_text = "\n".join(pages)

    parsed = parse_legislation_text(full_text)

    assert "OTOPARK YÖNETMELİĞİ" in parsed.title or "OTOPARK" in parsed.title
    assert len(parsed.articles) > 15

    # Madde 1 kontrolü
    art1_list = [a for a in parsed.articles if "Madde 1" in a.article]
    assert len(art1_list) >= 1
    assert "Yönetmeliğin amacı" in art1_list[0].text or "amac" in art1_list[0].text.lower()
    assert art1_list[0].paragraph == "1"

    # Madde 4 kontrolü (otopark genel esaslar)
    art4_list = [a for a in parsed.articles if "Madde 4" in a.article]
    assert len(art4_list) >= 1
    assert any("otopark" in a.topics for a in art4_list)


def test_parse_synthetic_multiparagraph_text():
    sample_text = """
    PLANLI ALANLAR İMAR YÖNETMELİĞİ

    MADDE 5 – (1) İmar planlarında su taşkın alanı olarak belirlenen yerlerde yapı yapılamaz.
    (2) Yapı ruhsatı alınmadan hiçbir yapının inşasına başlanamaz.
    (3) (Değişik:RG-1/7/2026-33297) Emsal hesabı, parsel sınırları içindeki net alan üzerinden yapılır.

    MADDE 6 – (1) Bu Yönetmelik yayımı tarihinde yürürlüğe girer.
    """

    parsed = parse_legislation_text(sample_text)
    assert parsed.title == "PLANLI ALANLAR İMAR YÖNETMELİĞİ"
    assert len(parsed.articles) == 4  # 3 fıkra (Madde 5) + 1 fıkra (Madde 6)

    m5_p3 = [a for a in parsed.articles if "Madde 5" in a.article and a.paragraph == "3"][0]
    assert "Emsal hesabı" in m5_p3.text
    assert "emsal" in m5_p3.topics
    assert any("RG-1/7/2026-33297" in am for am in m5_p3.amendments)
