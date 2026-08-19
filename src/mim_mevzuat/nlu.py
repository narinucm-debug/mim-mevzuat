"""NLU (Natural Language Understanding) & Query Understanding Module.

RAG_DESIGN.txt bölüm 2 ilkelerine uygun olarak:
Kullanıcının doğal dildeki mimari ifadelerini, sorularını ve proje parametrelerini
(parsel alanı, daire sayısı, KAKS, TAKS, mevcut otopark, ilçe vb.) anlar ve
otomatik olarak doğru kural motoruna veya retrieval katmanına yönlendirir.

Örnek Cümleler:
- "Çankaya'da 1500 m2 arsada emsal 1.50, 40 dairelik bir proje yapıyorum, 30 araçlık otopark yaptım, kurtarır mı?"
- "80 daire için kaç otopark yapmam lazım?"
- "Parsel 2000 m2, emsal 2.0, inşaat alanım 4500 m2 oldu aşım var mı?"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ExtractedEntities:
    jurisdiction: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    unit_count: Optional[int] = None
    units_under_80: Optional[int] = None
    units_80_to_140: Optional[int] = None
    units_over_140: Optional[int] = None
    parcel_area: Optional[float] = None
    kaks: Optional[float] = None
    taks: Optional[float] = None
    existing_parking: Optional[int] = None
    proposed_gross_area: Optional[float] = None
    exempt_area: Optional[float] = None
    building_type: str = "konut"


@dataclass
class ParsedUserIntent:
    raw_query: str
    intent: str  # "QA", "PARKING_CALC", "EMSAL_CALC", "PROJECT_CHECK"
    entities: ExtractedEntities
    detected_topics: list[str] = field(default_factory=list)
    confidence: float = 1.0


# İlçe / İl eşleştirme tablosu
_JURISDICTION_MAP = {
    "çankaya": "TR.Ankara.Cankaya",
    "cankaya": "TR.Ankara.Cankaya",
    "mamak": "TR.Ankara.Mamak",
    "gölbaşı": "TR.Ankara.Golbasi",
    "golbasi": "TR.Ankara.Golbasi",
    "etimesgut": "TR.Ankara.Etimesgut",
    "altındağ": "TR.Ankara.Altindag",
    "altindag": "TR.Ankara.Altindag",
    "pursaklar": "TR.Ankara.Pursaklar",
    "ankara": "TR.Ankara",
    "finike": "TR.Antalya.Finike",
    "antalya": "TR.Antalya",
    "istanbul": "TR.Istanbul",
    "izmir": "TR.Izmir",
}


def _parse_float(val_str: str) -> float:
    cleaned = val_str.replace(",", ".").strip()
    return float(cleaned)


def extract_entities_from_text(text: str) -> ExtractedEntities:
    """Metin içindeki mimari sayısal ve coğrafi parametreleri çıkarır."""
    low = text.lower()
    entities = ExtractedEntities()

    # 1. Konum / Jurisdiction
    for key, jur in _JURISDICTION_MAP.items():
        if re.search(rf"\b{key}\b", low):
            entities.jurisdiction = jur
            entities.district = key.title()
            break

    # 2. Daire / Bağımsız Bölüm Sayısı
    # Örnek: "40 dairelik", "80 daire", "25 bağımsız bölüm", "30 konut"
    unit_m = re.search(r"(\d+)\s*(?:adet\s*)?(?:daire|bağımsız\s*bölüm|konut|hane|birim)", low)
    if unit_m:
        entities.unit_count = int(unit_m.group(1))

    # Kademeli daire sayıları
    u80_m = re.search(r"(\d+)\s*(?:adet\s*)?(?:daire\s*)?(?:<80|80\s*m2\s*altı|küçük)", low)
    if u80_m:
        entities.units_under_80 = int(u80_m.group(1))

    # 3. Parsel / Arsa Alanı
    # Örnek: "1500 m2 arsa", "2000 m² parsel", "parsel 1200 m2", "parsel alanı 850"
    parcel_m = re.search(
        r"(?:parsel\s*(?:alanı)?|arsa\s*(?:alanı)?)\s*(?:[:=]|\s+olup|\s+olan)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metrekare)?",
        low,
    )
    if not parcel_m:
        parcel_m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metrekare)\s*(?:arsa|parsel)", low)
    if parcel_m:
        entities.parcel_area = _parse_float(parcel_m.group(1))

    # 4. KAKS / Emsal
    # Örnek: "emsal 1.50", "emsal: 2.0", "kaks 1.8", "emsali 1.60"
    kaks_m = re.search(r"(?:emsal|kaks|emsali)\s*[:=]?\s*(\d+(?:[.,]\d+)?)", low)
    if kaks_m:
        entities.kaks = _parse_float(kaks_m.group(1))

    # 5. TAKS / Taban Alanı Katsayısı
    # Örnek: "taks 0.40", "taks: 0.30", "taban alanı katsayısı 0.35"
    taks_m = re.search(r"(?:taks|taban\s*alanı\s*katsayısı)\s*[:=]?\s*(\d+(?:[.,]\d+)?)", low)
    if taks_m:
        entities.taks = _parse_float(taks_m.group(1))

    # 6. Mevcut / Planlanan Otopark Sayısı
    # Örnek: "30 araçlık otopark yaptım", "25 otopark koydum", "otopark sayısı 20", "15 araçlık otoparkım var"
    park_m = re.search(
        r"(\d+)\s*(?:araçlık|adet|tane)?\s*(?:otopark\s*(?:yaptım|koydum|var|ayırdım|planladım|çözdüm|mevcut)|otoparkım\s*var)",
        low,
    )
    if not park_m:
        park_m = re.search(r"(?:mevcut\s*otopark|otopark\s*kapasitesi)\s*[:=]?\s*(\d+)", low)
    if park_m:
        entities.existing_parking = int(park_m.group(1))

    # 7. İnşaat Alanı / Brüt Alan
    # Örnek: "toplam inşaat alanım 4500 m2", "inşaat alanı 5000 m2", "brüt 3000 m2", "alan 2400 m2 oldu"
    gross_m = re.search(
        r"(?:toplam\s+)?(?:inşaat\s+(?:alanı|alanım|alanımız|alan)?|brüt\s+(?:alanı|alanım|alan)?)\s*(?:[:=]|\s+oldu|\s+olan)?\s*(\d+(?:[.,]\d+)?)\s*(?:m2|m²|metrekare)?",
        low,
    )
    if not gross_m:
        gross_m = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:m2|m²)\s*(?:inşaat|brüt)", low)
    if gross_m:
        entities.proposed_gross_area = _parse_float(gross_m.group(1))

    return entities


def parse_user_intent(query: str) -> ParsedUserIntent:
    """Kullanıcı girdisini analiz ederek niyeti (Intent) ve çıkarılan parametreleri belirler."""
    entities = extract_entities_from_text(query)
    low = query.lower()

    detected_topics: list[str] = []
    if any(k in low for k in ["otopark", "park", "araç", "garaj", "şarj", "engelli park"]):
        detected_topics.append("otopark")
    if any(k in low for k in ["emsal", "kaks", "taks", "inşaat alanı", "aşım", "kat alanı"]):
        detected_topics.append("emsal")
    if any(k in low for k in ["yangın", "merdiven", "kaçış", "duman"]):
        detected_topics.append("yangin")
    if any(k in low for k in ["sığınak", "siginak"]):
        detected_topics.append("siginak")

    # Niyet Tespiti (Intent Classification)
    # Eğer hem daire sayısı hem otopark sorusu/rakamı varsa -> PARKING_CALC
    # Eğer hem parsel hem emsal/KAKS varsa -> EMSAL_CALC
    # Eğer her ikisi de varsa -> PROJECT_CHECK
    has_parking_params = entities.unit_count is not None or entities.existing_parking is not None
    has_emsal_params = entities.parcel_area is not None and entities.kaks is not None

    if has_parking_params and has_emsal_params:
        intent = "PROJECT_CHECK"
    elif has_parking_params and ("otopark" in detected_topics or "kurtarır" in low or "yeter" in low or "kaç" in low):
        intent = "PARKING_CALC"
    elif has_emsal_params and ("emsal" in detected_topics or "taks" in detected_topics or "aşım" in low or "kurtarır" in low):
        intent = "EMSAL_CALC"
    else:
        intent = "QA"

    return ParsedUserIntent(
        raw_query=query,
        intent=intent,
        entities=entities,
        detected_topics=detected_topics,
    )
