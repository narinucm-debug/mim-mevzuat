"""Architectural Interpreter - Mimari Mevzuat ve Hesap Yorumlama Motoru.

Kullanıcının "bide yorumlama olsa" talebi doğrultusunda:
Hesaplama sonuçlarını (CalculationTrace) ve mevzuat hükümlerini mimarlık pratiği,
ruhsat süreçleri ve proje çözümleri açısından uzman bir mimar gözüyle yorumlar.

Özellikler:
- Mimari Durum Tespiti (Verdict & Summary)
- Pratik Mimari Tasarım Tavsiyeleri ve Kurtarma Stratejileri (Örn. Otopark eksikliğinde 4 yasal çözüm)
- Emsal Harici Alan İpuçları (Bodrum otoparkı, yangın merdiveni, asansör, sığınak)
- Yerel İdare / Ruhsat Onay Riskleri (UKOME, Engelli Erişilebilirliği, EV Şarj)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .models import Evidence, ValidatedAnswer
from .rules.base import CalculationTrace


@dataclass
class ArchitecturalInterpretation:
    verdict: str                        # "UYGUN", "YETERSİZ / REVİZYON GEREKLİ", "KRİTİK UYARI"
    summary: str                        # Özet mimari değerlendirme
    compliance_notes: list[str] = field(default_factory=list)
    design_recommendations: list[str] = field(default_factory=list)
    authority_warnings: list[str] = field(default_factory=list)
    applicable_articles: list[str] = field(default_factory=list)


def interpret_calculation(
    trace: CalculationTrace,
    project_name: Optional[str] = None,
) -> ArchitecturalInterpretation:
    """Bir hesaplama sonucunu mimari proje perspektifinden yorumlar."""
    p_label = f"'{project_name}' projesi" if project_name else "Proje"
    res = trace.result
    rule_id = trace.rule_id

    # 1. KONUT OTOPARK HESABI YORUMU
    if "otopark" in rule_id:
        req = res.get("required_parking", 0)
        existing = res.get("existing_parking", 0)
        diff = res.get("difference", 0)
        acc = res.get("accessible_parking_required", 0)
        ev = res.get("ev_charging_parking_required", 0)
        status = res.get("status", "UYGUN")

        if status == "YETERSİZ" or diff < 0:
            deficit = abs(diff)
            verdict = "YETERSİZ / REVİZYON GEREKLİ"
            summary = (
                f"{p_label} için Otopark Yönetmeliği uyarınca en az {req} adet otopark gereklidir. "
                f"Mevcut projede {existing} adet ayrıldığından {deficit} araçlık OTOPARK EKSİĞİ bulunmaktadır. "
                f"Yapı ruhsatı alınabilmesi için bu açığın giderilmesi zorunludur."
            )
            recommendations = [
                f"1. [Bodrum Otoparkı]: Bodrum kat sayısı artırılarak otopark parsel içinde çözülebilir. "
                f"(Planlı Alanlar İmar Y. Madde 22 gereği tamamen toprak altında kalan bodrum otoparkları EMSALE DAHİL EDİLMEZ).",
                f"2. [Komşu Parsel / Ada İçi]: Otopark Yönetmeliği Madde 4(1)(f-1) uyarınca komşu parselle ortak otopark "
                f"veya ada içi ortak otopark protokolü yapılabilir.",
                f"3. [1500m / 2000m İrtifak]: Madde 4(1)(f-2) uyarınca 1500 m yarıçap veya 2000 m yürüme mesafesindeki "
                f"başka bir binadan tapuda süresiz irtifak kurularak otopark karşılanabilir.",
                f"4. [Belediye Bölge Otopark Bedeli]: Parselde fiziksel imkansızlık varsa Madde 4(1)(f-3) ve Madde 12 "
                f"gereğince belediyeye otopark bedeli ödenerek bölge otoparkından tahsis talep edilebilir.",
            ]
        else:
            verdict = "UYGUN"
            surplus = diff
            summary = (
                f"{p_label} otopark kapasitesi mevzuata uygundur. Gerekli {req} adede karşılık "
                f"{existing} adet otopark ayrılmıştır ({surplus} adet fazlalık/yedek kapasite mevcuttur)."
            )
            recommendations = [
                f"Parsel içi manevra alanlarının ve rampa eğimlerinin (Otopark Y. Madde 5 gereği binek otolar için max %15) "
                f"mimari avan projede net ölçülendirildiğinden emin olunmalıdır.",
                f"Giriş-çıkış genişliği tek yön için en az 2.75 m, çift yön için en az 5.00 m olarak projelendirilmelidir.",
            ]

        compliance = [
            f"Zorunlu Otopark Sayısı: {req} adet (Hesap: {trace.method.splitlines()[0]})",
            f"Engelli Otoparkı Zorunluluğu: En az {acc} adet (Giriş ve asansöre en yakın konumda olmalı - Madde 4/1-ı).",
        ]
        if ev > 0:
            compliance.append(
                f"Elektrikli Araç (EV) Şarj Yeri: En az {ev} adet şarj üniteli park yeri ayrılmalıdır (Kapasite 20+ olduğu için %5 zorunludur)."
            )

        warnings = [
            "UKOME / Yerel Trafik Komisyonu: Ana arter veya kavşak cepheli parsellerde otopark giriş-çıkışı için UKOME görüşü aranır.",
            "Yapı Ruhsatı ve İskan: Otopark yerleri vaziyet planında ve bağımsız bölüm listesinde açıkça gösterilmelidir.",
        ]

        return ArchitecturalInterpretation(
            verdict=verdict,
            summary=summary,
            compliance_notes=compliance,
            design_recommendations=recommendations,
            authority_warnings=warnings,
            applicable_articles=["Otopark Yönetmeliği Madde 4, 5, 10, 12", "Planlı Alanlar İmar Y. Madde 22"],
        )

    # 2. EMSAL VE TAKS HESABI YORUMU
    if "emsal" in rule_id or "imar" in rule_id:
        max_emsal = res.get("max_allowed_emsal_area", 0.0)
        actual = res.get("actual_emsal_area", 0.0)
        diff = res.get("difference", 0.0)
        max_taks = res.get("max_allowed_taks_area", 0.0)
        status = res.get("status", "UYGUN")

        if status == "EMSAL_ASIMI" or diff < 0:
            excess = abs(diff)
            verdict = "EMSAL AŞIMI / REVİZYON GEREKLİ"
            summary = (
                f"{p_label} için izin verilen maksimum emsal inşaat alanı {max_emsal:.2f} m²'dir. "
                f"Önerilen emsal alanı {actual:.2f} m² olup {excess:.2f} m² EMSAL AŞIMI tespit edilmiştir. "
                f"Projenin ruhsat alabilmesi için kütle veya alan revizyonu şarttır."
            )
            recommendations = [
                "1. [Emsal Harici Alan Analizi]: Planlı Alanlar İmar Yönetmeliği Madde 22'deki istisnaları kullanın:",
                "   - Tamamen toprak altında kalan bodrum otoparkları,",
                "   - Yangın kaçış merdivenleri ve yangın güvenlik holleri,",
                "   - Asansör boşlukları ve şaftlar,",
                "   - Sığınak, su deposu, trafo ve hidrofor odaları gibi ortak teknik alanlar emsalden düşülmelidir.",
                "2. [Kat Yüksekliği ve Taban Alanı]: TAKS sınırını aşmamak kaydıyla kat brüt alanları optimize edilebilir.",
            ]
        else:
            verdict = "UYGUN"
            summary = (
                f"{p_label} emsal hesabı uygundur. İzin verilen {max_emsal:.2f} m² inşaat hakkına karşılık "
                f"{actual:.2f} m² kullanılmış olup {diff:.2f} m² ilave emsal hakkı mevcuttur."
            )
            recommendations = [
                f"Kalan {diff:.2f} m² emsal hakkı bağımsız bölümlere veya ortak mekanlara dağıtılabilir.",
                f"Taban oturumunun max {max_taks:.2f} m² (TAKS sınırı) ve bahçe çekme mesafelerine uyduğu kontrol edilmelidir.",
            ]

        compliance = [
            f"Maksimum İzin Verilen Emsal Alanı: {max_emsal:.2f} m²",
            f"Kullanılan Emsale Esas Alan: {actual:.2f} m²",
            f"Kalan / Fark: {diff:.2f} m² ({status})",
        ]
        if max_taks > 0:
            compliance.append(f"Maksimum Taban Alanı (TAKS): {max_taks:.2f} m²")

        warnings = [
            "İmar Planı Notları: İlgili belediyenin 1/1000 uygulama imar plan notlarında özel emsal/yükseklik kısıtı olup olmadığı kontrol edilmelidir.",
            "Kot Kesit & Çekme Mesafeleri: Yoldan ve tabii zeminden alınan kotlar emsal harici bodrum kat sınırını doğrudan etkiler.",
        ]

        return ArchitecturalInterpretation(
            verdict=verdict,
            summary=summary,
            compliance_notes=compliance,
            design_recommendations=recommendations,
            authority_warnings=warnings,
            applicable_articles=["Planlı Alanlar İmar Yönetmeliği Madde 4, 5, 22"],
        )

    # Genel Kural Yorumu
    return ArchitecturalInterpretation(
        verdict="HESAPLANDI",
        summary=f"{trace.rule_name} başarıyla uygulandı.",
        compliance_notes=[f"Sonuç: {res}"],
        design_recommendations=["Mimari projede ilgili mevzuat hükümlerine göre detaylandırılmalıdır."],
        authority_warnings=["İlgili idare onayına tabidir."],
        applicable_articles=[f"{trace.source_document} {trace.source_article}"],
    )
