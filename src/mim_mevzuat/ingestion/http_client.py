"""mevzuat.gov.tr erişimi için HTTP istemcisi.

Bu modül, 2026-08-19'da tespit edilen iki ayrı erişim engelini KÖK
NEDENİNDEN çözer (SECURITY.txt ilkelerine uygun biçimde - sertifika
doğrulamasını KAPATMADAN):

  1. mevzuat.gov.tr, TLS el sıkışmasında ara sertifikayı (GeoTrust TLS
     RSA CA G1) göndermiyor - bu bir sunucu yanlış yapılandırmasıdır.
     `openssl s_client -showcerts` ile doğrulandı: sunucu yalnızca yaprak
     sertifikayı (*.tccb.gov.tr) sunuyor. Windows schannel (curl'ün bu
     makinede kullandığı) AIA ile eksik sertifikayı otomatik tamamlıyor;
     Python/requests gibi kütüphaneler tamamlamıyor ve reddediyor.
     ÇÖZÜM: eksik ara sertifika bu pakette (certs/geotrust_tls_rsa_ca_g1.pem)
     saklanır ve certifi'nin varsayılan güven demetine EKLENEREK
     kullanılır - `verify=False` YOLUNA GİDİLMEZ, tam doğrulama korunur.

  2. Sunucu, tarayıcı benzeri olmayan isteklere (ör. curl varsayılan
     User-Agent'ı, HEAD metodu) yanıt vermeden bağlantıyı askıda
     bırakıyor (muhtemelen bir WAF/bot filtresi). ÇÖZÜM: gerçekçi bir
     tarayıcı User-Agent'ı ve GET metodu kullanmak.

Kanıt/tekrarlanabilirlik notu: bu iki bulgu curl/openssl ile manuel
doğrulandı (bkz. SOURCE_MAP.txt "Doğrulama Notu - Kök Neden Analizi").
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import certifi
import requests

_INTERMEDIATE_CERT_PATH = Path(__file__).parent / "certs" / "geotrust_tls_rsa_ca_g1.pem"

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

_merged_ca_bundle_path: str | None = None


def _merged_ca_bundle() -> str:
    """certifi'nin varsayılan demetine eksik mevzuat.gov.tr ara
    sertifikasını ekleyip birleşik bir dosya yolu döner. Süreç başına
    bir kez hesaplanır (tekrar tekrar geçici dosya yazmamak için)."""

    global _merged_ca_bundle_path
    if _merged_ca_bundle_path is not None:
        return _merged_ca_bundle_path

    default_bundle = Path(certifi.where()).read_bytes()
    extra_cert = _INTERMEDIATE_CERT_PATH.read_bytes()

    merged = tempfile.NamedTemporaryFile(
        delete=False, suffix=".pem", prefix="mim_mevzuat_ca_bundle_"
    )
    merged.write(default_bundle)
    merged.write(b"\n")
    merged.write(extra_cert)
    merged.close()

    _merged_ca_bundle_path = merged.name
    return _merged_ca_bundle_path


def build_session() -> requests.Session:
    """mevzuat.gov.tr'den güvenli (tam sertifika doğrulamalı) ve
    başarılı (WAF'ı tetiklemeyen) istek atabilen bir requests.Session
    döner."""

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": BROWSER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/pdf",
        }
    )
    session.verify = _merged_ca_bundle()
    return session
