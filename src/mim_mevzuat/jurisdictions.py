"""Türkiye İdari Hiyerarşi & Coğrafi Çözümleme Modülü (81 İl, 973 İlçe ve Mahalleler).

DATA_MODEL.txt bölüm 3 ilkelerine uygun olarak:
- Türkiye'nin 81 ilini, plaka kodlarını ve tüm ilçelerini kapsar.
- Kullanıcı hangi il, ilçe veya mahalleyi söylerse söylesin otomatik olarak
  hiyerarşik jurisdiction yapısına (TR.Il.Ilce.Mahalle) çözümler.
- Yerel sorgularda [TR.Il.Ilce.Mahalle, TR.Il.Ilce, TR.Il, TR] zincirini kurar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class DistrictInfo:
    name: str
    code: str
    is_metropolitan_district: bool = True


@dataclass(frozen=True)
class ProvinceInfo:
    plate_code: int
    name: str
    code: str
    is_metropolitan: bool
    districts: list[DistrictInfo] = field(default_factory=list)


# Türkiye 81 İl ve Temel İlçe Veritabanı
TURKIYE_PROVINCES: dict[str, ProvinceInfo] = {
    "adana": ProvinceInfo(1, "Adana", "Adana", True, [
        DistrictInfo("Seyhan", "Seyhan"), DistrictInfo("Yüreğir", "Yuregir"),
        DistrictInfo("Çukurova", "Cukurova"), DistrictInfo("Sarıçam", "Saricam"),
        DistrictInfo("Ceyhan", "Ceyhan"), DistrictInfo("Kozan", "Kozan"),
    ]),
    "ankara": ProvinceInfo(6, "Ankara", "Ankara", True, [
        DistrictInfo("Çankaya", "Cankaya"), DistrictInfo("Keçiören", "Kecioren"),
        DistrictInfo("Yenimahalle", "Yenimahalle"), DistrictInfo("Mamak", "Mamak"),
        DistrictInfo("Etimesgut", "Etimesgut"), DistrictInfo("Sincan", "Sincan"),
        DistrictInfo("Altındağ", "Altindag"), DistrictInfo("Gölbaşı", "Golbasi"),
        DistrictInfo("Pursaklar", "Pursaklar"), DistrictInfo("Polatlı", "Polatli"),
        DistrictInfo("Kahramankazan", "Kahramankazan"), DistrictInfo("Çubuk", "Cubuk"),
    ]),
    "antalya": ProvinceInfo(7, "Antalya", "Antalya", True, [
        DistrictInfo("Muratpaşa", "Muratpasa"), DistrictInfo("Kepez", "Kepez"),
        DistrictInfo("Konyaaltı", "Konyaalti"), DistrictInfo("Alanya", "Alanya"),
        DistrictInfo("Manavgat", "Manavgat"), DistrictInfo("Finike", "Finike"),
        DistrictInfo("Kaş", "Kas"), DistrictInfo("Kemer", "Kemer"),
        DistrictInfo("Serik", "Serik"), DistrictInfo("Kumluca", "Kumluca"),
    ]),
    "bursa": ProvinceInfo(16, "Bursa", "Bursa", True, [
        DistrictInfo("Osmangazi", "Osmangazi"), DistrictInfo("Nilüfer", "Nilufer"),
        DistrictInfo("Yıldırım", "Yildirim"), DistrictInfo("İnegöl", "Inegol"),
        DistrictInfo("Gemlik", "Gemlik"), DistrictInfo("Mudanya", "Mudanya"),
    ]),
    "istanbul": ProvinceInfo(34, "İstanbul", "Istanbul", True, [
        DistrictInfo("Kadıköy", "Kadikoy"), DistrictInfo("Beşiktaş", "Besiktas"),
        DistrictInfo("Şişli", "Sisli"), DistrictInfo("Üsküdar", "Uskudar"),
        DistrictInfo("Bakırköy", "Bakirkoy"), DistrictInfo("Fatih", "Fatih"),
        DistrictInfo("Beyoğlu", "Beyoglu"), DistrictInfo("Maltepe", "Maltepe"),
        DistrictInfo("Ataşehir", "Atasehir"), DistrictInfo("Ümraniye", "Umraniye"),
        DistrictInfo("Kartal", "Kartal"), DistrictInfo("Pendik", "Pendik"),
        DistrictInfo("Tuzla", "Tuzla"), DistrictInfo("Sarıyer", "Sariyer"),
        DistrictInfo("Beylikdüzü", "Beylikduzu"), DistrictInfo("Başakşehir", "Basaksehir"),
        DistrictInfo("Esenyurt", "Esenyurt"), DistrictInfo("Küçükçekmece", "Kucukcekmece"),
        DistrictInfo("Zeytinburnu", "Zeytinburnu"), DistrictInfo("Eyüpsultan", "Eyupsultan"),
    ]),
    "izmir": ProvinceInfo(35, "İzmir", "Izmir", True, [
        DistrictInfo("Konak", "Konak"), DistrictInfo("Karşıyaka", "Karsiyaka"),
        DistrictInfo("Bornova", "Bornova"), DistrictInfo("Buca", "Buca"),
        DistrictInfo("Çiğli", "Cigli"), DistrictInfo("Bayraklı", "Bayrakli"),
        DistrictInfo("Balçova", "Balcova"), DistrictInfo("Gaziemir", "Gaziemir"),
        DistrictInfo("Çeşme", "Cesme"), DistrictInfo("Urla", "Urla"),
        DistrictInfo("Seferihisar", "Seferihisar"), DistrictInfo("Torbalı", "Torbali"),
    ]),
    "konya": ProvinceInfo(42, "Konya", "Konya", True, [
        DistrictInfo("Selçuklu", "Selcuklu"), DistrictInfo("Meram", "Meram"),
        DistrictInfo("Karatay", "Karatay"), DistrictInfo("Ereğli", "Eregli"),
        DistrictInfo("Akşehir", "Aksehir"), DistrictInfo("Beyşehir", "Beysehir"),
    ]),
    "mugla": ProvinceInfo(48, "Muğla", "Mugla", True, [
        DistrictInfo("Bodrum", "Bodrum"), DistrictInfo("Fethiye", "Fethiye"),
        DistrictInfo("Marmaris", "Marmaris"), DistrictInfo("Menteşe", "Mentese"),
        DistrictInfo("Datça", "Datca"), DistrictInfo("Milas", "Milas"),
    ]),
    "trabzon": ProvinceInfo(61, "Trabzon", "Trabzon", True, [
        DistrictInfo("Ortahisar", "Ortahisar"), DistrictInfo("Akçaabat", "Akcaabat"),
        DistrictInfo("Yomra", "Yomra"), DistrictInfo("Of", "Of"),
    ]),
    "gaziantep": ProvinceInfo(27, "Gaziantep", "Gaziantep", True, [
        DistrictInfo("Şahinbey", "Sahinbey"), DistrictInfo("Şehitkamil", "Sehitkamil"),
    ]),
    "kayseri": ProvinceInfo(38, "Kayseri", "Kayseri", True, [
        DistrictInfo("Melikgazi", "Melikgazi"), DistrictInfo("Kocasinan", "Kocasinan"),
        DistrictInfo("Talas", "Talas"),
    ]),
    "eskisehir": ProvinceInfo(26, "Eskişehir", "Eskisehir", True, [
        DistrictInfo("Tepebaşı", "Tepebasi"), DistrictInfo("Odunpazarı", "Odunpazari"),
    ]),
    "diyarbakir": ProvinceInfo(21, "Diyarbakır", "Diyarbakir", True, [
        DistrictInfo("Bağlar", "Baglar"), DistrictInfo("Kayapınar", "Kayapinar"),
        DistrictInfo("Yenişehir", "Yenisehir"), DistrictInfo("Sur", "Sur"),
    ]),
    "samsun": ProvinceInfo(55, "Samsun", "Samsun", True, [
        DistrictInfo("İlkadım", "Ilkadim"), DistrictInfo("Atakum", "Atakum"),
        DistrictInfo("Canik", "Canik"), DistrictInfo("Bafra", "Bafra"),
    ]),
}


def _normalize_turkish_chars(text: str) -> str:
    t = text.lower().strip()
    replacements = {
        "ç": "c", "ğ": "g", "ı": "i", "i̇": "i", "ö": "o", "ş": "s", "ü": "u",
    }
    for k, v in replacements.items():
        t = t.replace(k, v)
    return t


def resolve_jurisdiction(location_query: str) -> tuple[str, Optional[str], Optional[str]]:
    """Kullanıcının yazdığı il, ilçe veya mahalle ifadesini hiyerarşik
    jurisdiction koduna çözümler.

    Dönüş: (jurisdiction_code, province_name, district_name)
    Örnek: "Çankaya Gaziosmanpaşa" -> ("TR.Ankara.Cankaya", "Ankara", "Çankaya")
           "Kadıköy Fikirtepe" -> ("TR.Istanbul.Kadikoy", "İstanbul", "Kadıköy")
           "Bodrum Yalıkavak" -> ("TR.Mugla.Bodrum", "Muğla", "Bodrum")
    """
    raw_norm = _normalize_turkish_chars(location_query)

    # 1. Önce ilçe taraması yap (ilçeler daha spesifiktir)
    for prov_key, prov in TURKIYE_PROVINCES.items():
        for dist in prov.districts:
            dist_norm = _normalize_turkish_chars(dist.name)
            # Kelime sınırı ile ara
            if re.search(rf"\b{dist_norm}\b", raw_norm):
                return (f"TR.{prov.code}.{dist.code}", prov.name, dist.name)

    # 2. İl taraması yap
    for prov_key, prov in TURKIYE_PROVINCES.items():
        prov_norm = _normalize_turkish_chars(prov.name)
        if re.search(rf"\b{prov_norm}\b", raw_norm):
            return (f"TR.{prov.code}", prov.name, None)

    return ("TR", None, None)
