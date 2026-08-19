"""Otopark Rule Pack'leri - Otopark Yönetmeliği (ve değişiklikleri) uyarınca
deterministik otopark gereksinimi, engelli park yeri ve EV şarj yeri hesabı.
"""

from __future__ import annotations

import math
from typing import Any

from .base import RuleInput, RulePack


def _calculate_residential_parking(inputs: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Konut Otopark Hesabı Formülü:
    - 100 m2 altı daire sayısı (her 3 daireye en az 1) veya varsayılan 1 daire = 1 otopark
    - Toplam gerekli otopark = ceil(hesaplanan)
    - Engelli Otoparkı = ceil(Toplam / 20) (Madde 4(1)(ı))
    - EV Şarj Yeri = ceil(Toplam * 0.05) eğer Toplam >= 20 ise (Madde 4)
    """
    unit_count = inputs["unit_count"]
    existing_parking = inputs.get("existing_parking", 0)

    # Daire büyüklükleri verilmişse detaylı hesap, verilmemişse 1 daire = 1 otopark
    units_under_80 = inputs.get("units_under_80", 0)
    units_80_to_140 = inputs.get("units_80_to_140", 0)
    units_over_140 = inputs.get("units_over_140", 0)

    if units_under_80 + units_80_to_140 + units_over_140 > 0:
        # Alan kademeli hesap: <80m2: 1/3, 80-140m2: 1/2, >140m2: 1/1
        raw_req = (units_under_80 / 3.0) + (units_80_to_140 / 2.0) + (units_over_140 * 1.0)
        required_parking = math.ceil(raw_req)
        method_desc = (
            f"Kademeli Konut Otopark Hesabı:\n"
            f"- <80 m² ({units_under_80} adet): {units_under_80}/3 = {units_under_80/3.0:.2f}\n"
            f"- 80-140 m² ({units_80_to_140} adet): {units_80_to_140}/2 = {units_80_to_140/2.0:.2f}\n"
            f"- >140 m² ({units_over_140} adet): {units_over_140} x 1 = {units_over_140:.2f}\n"
            f"Toplam Gerekli: {required_parking} araçlık park yeri."
        )
    else:
        # Standart 1 birim = 1 otopark
        required_parking = int(unit_count)
        method_desc = f"Standart Konut Otopark Hesabı: {unit_count} bağımsız bölüm için {required_parking} adet otopark."

    # Engelli otoparkı: Her 20 araçtan 1'i (en az 1 adet)
    accessible_parking = math.ceil(required_parking / 20.0) if required_parking > 0 else 0

    # EV Şarj yeri: 20 ve üzeri otopark kapasiteli binalarda en az %5
    if required_parking >= 20:
        ev_parking = math.ceil(required_parking * 0.05)
    else:
        ev_parking = 0

    diff = existing_parking - required_parking
    status = "UYGUN" if diff >= 0 else "YETERSİZ"

    result = {
        "required_parking": required_parking,
        "existing_parking": existing_parking,
        "difference": diff,
        "status": status,
        "accessible_parking_required": accessible_parking,
        "ev_charging_parking_required": ev_parking,
        "deficit": abs(diff) if diff < 0 else 0,
    }

    return result, method_desc


RULE_OTOPARK_KONUT = RulePack(
    rule_id="rule:otopark:konut:v2022",
    name="Konut Yapıları Otopark İhtiyacı Hesabı",
    jurisdiction="TR",
    version="2022.06",
    source_document="yonetmelik:7.5.24408",
    source_article="Madde 4, Madde 10",
    inputs=[
        RuleInput("unit_count", "int", required=True, description="Toplam konut bağımsız bölüm sayısı"),
        RuleInput("existing_parking", "int", required=False, default=0, description="Projeye ayrılan mevcut otopark sayısı"),
        RuleInput("units_under_80", "int", required=False, default=0, description="Brüt alanı 80 m²'nin altındaki daire sayısı"),
        RuleInput("units_80_to_140", "int", required=False, default=0, description="Brüt alanı 80-140 m² arasındaki daire sayısı"),
        RuleInput("units_over_140", "int", required=False, default=0, description="Brüt alanı 140 m²'nin üzerindeki daire sayısı"),
    ],
    formula_fn=_calculate_residential_parking,
    conditions=["Konut kullanımına ayrılmış binalar"],
    exceptions=["Sit alanları veya UKOME tarafından giriş-çıkışa izin verilmeyen yollar"],
)
