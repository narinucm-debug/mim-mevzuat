"""Emsal (KAKS) ve TAKS Rule Pack'leri - Planlı Alanlar İmar Yönetmeliği
uyarınca taban alanı, emsal alanı, katlar alanı ve emsal aşımı hesabı.
"""

from __future__ import annotations

from typing import Any

from .base import RuleInput, RulePack


def _calculate_emsal_and_taks(inputs: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Emsal (KAKS) ve Taban Alanı (TAKS) Hesap Formülü:
    - Parsel Alanı (m2)
    - TAKS (Taban Alanı Katsayısı, ör. 0.30) -> Max Taban Alanı = Parsel * TAKS
    - KAKS (Emsal, ör. 1.50) -> Max Emsale Esas Alan = Parsel * KAKS
    - Önerilen / Mevcut Emsale Dahil Alan (m2)
    - Emsal Harici Alanlar (Bodrum otopark, sığınak, asansör/merdiven boşluğu vb.)
    - Durum: UYGUN veya EMSAL AŞIMI
    """
    parcel_area = float(inputs["parcel_area"])
    kaks = float(inputs["kaks"])
    taks = float(inputs.get("taks", 0.0))

    proposed_gross_area = float(inputs.get("proposed_gross_area", 0.0))
    exempt_area = float(inputs.get("exempt_area", 0.0))  # Emsale dahil edilmeyecek alanlar

    max_taks_area = parcel_area * taks if taks > 0 else 0.0
    max_kaks_area = parcel_area * kaks

    # Emsale esas inşaat alanı = Toplam brüt - Emsal harici alanlar
    if proposed_gross_area > 0:
        actual_emsal_area = max(0.0, proposed_gross_area - exempt_area)
    else:
        actual_emsal_area = float(inputs.get("actual_emsal_area", 0.0))

    diff = max_kaks_area - actual_emsal_area
    status = "UYGUN" if diff >= 0 else "EMSAL_ASIMI"

    method_desc = (
        f"Emsal ve Taban Alanı Hesabı (Madde 4, 5, 22):\n"
        f"- Parsel Alanı: {parcel_area:.2f} m²\n"
        f"- Emsal (KAKS): {kaks:.2f} -> İzin Verilen Max Emsal Alanı = {parcel_area:.2f} x {kaks:.2f} = {max_kaks_area:.2f} m²\n"
    )
    if taks > 0:
        method_desc += f"- TAKS: {taks:.2f} -> Max Taban Alanı = {parcel_area:.2f} x {taks:.2f} = {max_taks_area:.2f} m²\n"

    if actual_emsal_area > 0:
        method_desc += (
            f"- Kullanılan Emsal Alanı: {actual_emsal_area:.2f} m² "
            f"(Brüt: {proposed_gross_area:.2f} m², Emsal Harici: {exempt_area:.2f} m²)\n"
            f"- Kalan Emsal Hakkı: {diff:.2f} m² ({status})"
        )

    result = {
        "parcel_area": parcel_area,
        "kaks": kaks,
        "taks": taks,
        "max_allowed_emsal_area": round(max_kaks_area, 2),
        "max_allowed_taks_area": round(max_taks_area, 2),
        "actual_emsal_area": round(actual_emsal_area, 2),
        "exempt_area": round(exempt_area, 2),
        "difference": round(diff, 2),
        "status": status,
        "excess_area": round(abs(diff), 2) if diff < 0 else 0.0,
    }

    return result, method_desc


RULE_EMSAL_TAKS = RulePack(
    rule_id="rule:imar:emsal_taks:v2026",
    name="Emsal (KAKS) ve Taban Alanı (TAKS) Hesabı",
    jurisdiction="TR",
    version="2026.07",
    source_document="yonetmelik:7.5.23722",
    source_article="Madde 4, Madde 5, Madde 22",
    inputs=[
        RuleInput("parcel_area", "float", required=True, description="Net imar parseli alanı (m²)"),
        RuleInput("kaks", "float", required=True, description="Emsal katsayısı (KAKS)"),
        RuleInput("taks", "float", required=False, default=0.0, description="Taban alanı kat sayısı (TAKS)"),
        RuleInput("proposed_gross_area", "float", required=False, default=0.0, description="Önerilen toplam brüt inşaat alanı (m²)"),
        RuleInput("exempt_area", "float", required=False, default=0.0, description="Emsale dahil edilmeyecek ortak/teknik alanlar toplamı (m²)"),
        RuleInput("actual_emsal_area", "float", required=False, default=0.0, description="Doğrudan girilen emsale esas alan (m²)"),
    ],
    formula_fn=_calculate_emsal_and_taks,
    conditions=["Planlı alanlar kapsamındaki imar parselleri"],
    exceptions=["Özel kanunlara tabi sit ve koruma alanları"],
)
