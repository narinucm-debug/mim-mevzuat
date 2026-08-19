"""CANLI AĞ testi - varsayılan hızlı test koşusunun parçası DEĞİLDİR.

Çalıştırmak için: pytest -m network tests/integration/
Varsayılan `pytest tests/` koşusu bunu ATLAR (pyproject.toml'daki
`-m "not network"` varsayılanı, bkz. addopts).

Amaç: http_client.py'deki TLS/User-Agent düzeltmesinin gerçekten
mevzuat.gov.tr'ye karşı çalıştığını düzenli olarak doğrulamak - kaynak
sitenin davranışı değişirse (ör. sertifikasını düzeltirse, WAF
kurallarını değiştirirse) bu test SESSİZCE eskimek yerine kırılıp
haber verir."""

import pytest

from mim_mevzuat.ingestion.mevzuat_gov_tr import extract_text_by_page, fetch_consolidated_pdf

pytestmark = pytest.mark.network


def test_live_fetch_otopark_yonetmeligi_pdf():
    doc = fetch_consolidated_pdf("7.5.24408")

    assert doc.content_type == "application/pdf"
    assert len(doc.raw_bytes) > 1000

    pages = extract_text_by_page(doc.raw_bytes)
    full_text = "\n".join(pages)
    assert "OTOPARK YÖNETMELİĞİ" in full_text
    assert "MADDE 1" in full_text
