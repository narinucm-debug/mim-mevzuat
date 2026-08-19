"""PDF metin çıkarımı testleri - ağ gerektirmez, gerçek bir mevzuat.gov.tr
belgesinin (Otopark Yönetmeliği konsolide PDF'i) örneği fixture olarak
saklanır. Bu, "Türkçe karakterler (İ,ı,Ş,ş,Ğ,ğ,Ç,ç,Ö,ö,Ü,ü) doğru
çıkarılıyor mu" sorusunu somut olarak kanıtlar - 2026-08-19'da bu
karakterlerin konsol/terminal görüntüleme sorunuyla (UTF-8 olmayan
codepage) karıştırıldığı, ama gerçek veride SORUN OLMADIĞI keşfedildi."""

from pathlib import Path

from mim_mevzuat.ingestion.mevzuat_gov_tr import extract_text_by_page, has_native_text_layer

FIXTURE = Path(__file__).parent / "fixtures" / "otopark_yonetmeligi_sample.pdf"


def test_extracts_ten_pages():
    pages = extract_text_by_page(FIXTURE.read_bytes())
    assert len(pages) == 10


def test_first_article_text_is_correct_with_turkish_characters():
    pages = extract_text_by_page(FIXTURE.read_bytes())
    full_text = "\n".join(pages)

    assert "OTOPARK YÖNETMELİĞİ" in full_text
    assert "MADDE 1" in full_text
    assert "Yönetmeliğin amacı" in full_text
    assert "İmar Kanunu" in full_text
    assert "�" not in full_text  # replacement char yok - kayip veri yok


def test_inline_amendment_markers_are_preserved():
    """mevzuat.gov.tr konsolide metni, degisen hukumleri inline olarak
    hangi Resmi Gazete tarihinde degistigini isaretliyor - bu,
    UPDATE_ENGINE.txt'nin versiyonlama varsayimini dogrudan destekler."""
    pages = extract_text_by_page(FIXTURE.read_bytes())
    full_text = "\n".join(pages)

    assert "Değişik" in full_text
    assert "RG-" in full_text


def test_fixture_has_native_text_layer():
    assert has_native_text_layer(FIXTURE.read_bytes()) is True
