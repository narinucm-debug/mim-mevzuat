"""Mevzuat Asistanı Çekirdeği - NLU, RETRIEVAL, RULE ENGINE, INTERPRETER,
ANSWER COMPOSER ve CITATION ENFORCER bileşenlerini yöneten ana sınıf.

Kullanıcının doğal dildeki sorularını ("dediklerimi anlasa" ve "yorumlasa")
otomatik analiz eder, gerekirse kural motoruyla deterministik hesap yapar ve
uzman mimari yorumu (`ArchitecturalInterpretation`) ile doğrulanmış cevabı üretir.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .composer import AnswerComposer
from .db import apply_schema, connect
from .ingestion.pipeline import DocumentMetadata, ingest_pdf_file, ingest_text
from .interpreter import ArchitecturalInterpretation, interpret_calculation
from .models import Citation, ConfidenceLevel, Evidence, ValidatedAnswer, ValidationResult
from .nlu import ExtractedEntities, ParsedUserIntent, parse_user_intent
from .providers import LLMProvider, MockGroundedProvider
from .retrieval import QueryFilter, RetrievalEngine
from .rules.base import CalculationTrace
from .rules.engine import RuleEngine

# Varsayılan temel yönetmelik fixture'ları
DEFAULT_OTOPARK_PDF = Path(__file__).parent.parent.parent / "tests" / "fixtures" / "otopark_yonetmeligi_sample.pdf"

PLANLI_ALANLAR_CORE_TEXT = """
PLANLI ALANLAR İMAR YÖNETMELİĞİ

MADDE 1 – (1) Bu Yönetmeliğin amacı, plan, fen, sağlık ve sürdürülebilir çevre şartlarına uygun yapı ve yapılaşma ortamının sağlanmasına ilişkin usul ve esasları düzenlemektir.

MADDE 4 – (1) Bu Yönetmelikte geçen;
a) Emsal (Kat alanı kat sayısı - KAKS): Yapının kat alanları toplamının parsel alanına oranını gösteren sayıdır.
b) Taban alanı kat sayısı (TAKS): Taban alanının parsel alanına oranını gösteren sayıdır.
c) Yapı inşaat alanı: Işıklıklar ve avlular hariç olmak üzere, bodrum kat, asma kat ve çatı arasında yer alan mekanlar, ahşap ve kargir sundurmalar dahil, yapının inşa edilen bütün katlarının toplam alanıdır.

MADDE 5 – (1) İmar planlarında su taşkın alanı olarak belirlenen yerlerde yapı yapılamaz.
(2) Yapı ruhsatı alınmadan hiçbir yapının inşasına başlanamaz.
(3) Emsal hesabı, imar parseli alanı üzerinden belirlenir.

MADDE 22 – (1) Emsal hesabına (Kat Alanları Toplamına) dahil edilmeyecek alanlar şunlardır:
a) Tamamen toprağın altında kalan bodrum katlarda yer alan ve zorunlu otopark olarak kullanılan alanlar,
b) Sığınak, yangın kaçış merdiveni, asansör boşlukları, su deposu ve hidrofor odası gibi ortak alanlar,
c) Açık yüzme havuzu, açık spor sahaları ve bahçe düzenlemeleri emsale dahil edilmez.
"""

YANGIN_YONETMELIGI_CORE_TEXT = """
BİNALARIN YANGINDAN KORUNMASI HAKKINDA YÖNETMELİK

MADDE 1 – (1) Bu Yönetmeliğin amacı; her türlü yapı, bina, tesis ve işletmede yangın güvenliğini sağlamaktır.

MADDE 30 – (1) Kaçış Merdivenleri: Yapı yüksekliği 21.50 m'nin veya bina yüksekliği 30.50 m'nin üzerindeki konut yapılarında en az 2 adet yangın kaçış merdiveni yapılması zorunludur.

MADDE 34 – (1) Yangın güvenlik holleri, kaçış merdivenlerine duman ve alev geçişini engellemek amacıyla düzenlenir ve en az 3 m² taban alanına sahip olmalıdır.
"""

SIGINAK_YONETMELIGI_CORE_TEXT = """
SIĞINAK YÖNETMELİĞİ

MADDE 1 – (1) Bu Yönetmeliğin amacı, sığınakların yapılması, tefrişi, korunması ve kullanılmasına ilişkin usul ve esasları belirlemektir.

MADDE 7 – (1) Sığınak Yapılması Zorunlu Binalar: 12 veya daha fazla bağımsız bölümü olan konut yapılarında ve toplam inşaat alanı 800 m²'yi aşan umumi ve ticari binalarda serpinti sığınağı yapılması zorunludur.

MADDE 8 – (1) Sığınak Alanı: Sığınak alanı, kişi başına en az 1 m² net alan ve 3 m³ hacim düşecek şekilde projelendirilir.
"""


@dataclass
class ExecutionTrace:
    trace_id: str
    query: str
    jurisdiction: Optional[str]
    intent: Optional[ParsedUserIntent]
    evidence_found: list[Evidence]
    validated_answer: ValidatedAnswer
    validation_result: ValidationResult
    calculation_traces: list[CalculationTrace] = field(default_factory=list)
    interpretation: Optional[ArchitecturalInterpretation] = None
    duration_ms: float = 0.0
    created_at: str = ""


class MevzuatAssistant:
    def __init__(
        self,
        db_path: str | Path = ":memory:",
        provider: Optional[LLMProvider] = None,
        auto_seed: bool = True,
    ):
        self.conn = connect(db_path, check_same_thread=False)
        apply_schema(self.conn)
        self.retrieval = RetrievalEngine(self.conn)
        self.composer = AnswerComposer(provider=provider or MockGroundedProvider())

        if auto_seed:
            self.seed_core_regulations()

        self.rule_engine = RuleEngine(self.conn)

    def seed_core_regulations(self) -> None:
        """Çekirdek yönetmelikleri (Otopark, Planlı Alanlar, Yangın, Sığınak) yükler."""
        # 1. Otopark Yönetmeliği
        if DEFAULT_OTOPARK_PDF.exists():
            meta_otopark = DocumentMetadata(
                document_id="yonetmelik:7.5.24408",
                title="Otopark Yönetmeliği",
                authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
                document_type="yonetmelik",
                jurisdiction="TR",
                publication_date="2018-02-22",
                effective_date="2018-06-01",
                version="2022.06",
                source_url="https://www.mevzuat.gov.tr/MevzuatMetin/yonetmelik/7.5.24408.pdf",
                validity_status="ACTIVE",
            )
            ingest_pdf_file(self.conn, meta_otopark, DEFAULT_OTOPARK_PDF)

        # 2. Planlı Alanlar İmar Yönetmeliği
        meta_planli = DocumentMetadata(
            document_id="yonetmelik:7.5.23722",
            title="Planlı Alanlar İmar Yönetmeliği",
            authority="Çevre, Şehircilik ve İklim Değişikliği Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2017-07-03",
            effective_date="2017-10-01",
            version="2026.07",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=23722&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_planli, PLANLI_ALANLAR_CORE_TEXT)

        # 3. Yangın Yönetmeliği
        meta_yangin = DocumentMetadata(
            document_id="yonetmelik:200712937",
            title="Binaların Yangından Korunması Hakkında Yönetmelik",
            authority="İçişleri ve Çevre Bakanlığı",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="2007-12-19",
            effective_date="2007-12-19",
            version="2025.07",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=200712937&MevzuatTur=21&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_yangin, YANGIN_YONETMELIGI_CORE_TEXT)

        # 4. Sığınak Yönetmeliği
        meta_siginak = DocumentMetadata(
            document_id="yonetmelik:7.5.4883",
            title="Sığınak Yönetmeliği",
            authority="İçişleri Bakanlığı / AFAD",
            document_type="yonetmelik",
            jurisdiction="TR",
            publication_date="1988-10-25",
            effective_date="1988-10-25",
            version="2025.11",
            source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=4883&MevzuatTur=7&MevzuatTertip=5",
            validity_status="ACTIVE",
        )
        ingest_text(self.conn, meta_siginak, SIGINAK_YONETMELIGI_CORE_TEXT)

    def ask(
        self,
        query: str,
        jurisdiction: Optional[str] = None,
        limit: int = 5,
    ) -> ExecutionTrace:
        """Kullanıcının doğal dil sorgusunu anlar (NLU), hesaplar, yorumlar ve cevaplar."""
        t0 = time.perf_counter()
        trace_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()

        # 1. NLU / DOĞAL DİL ANLAMA
        user_intent = parse_user_intent(query)
        effective_jurisdiction = jurisdiction or user_intent.entities.jurisdiction or "TR"

        calc_traces: list[CalculationTrace] = []
        interpretation: Optional[ArchitecturalInterpretation] = None

        # 2. HESAPLAMA MOTORU ÇALIŞTIRMA (Entities varsa otomatik çalıştır)
        ent = user_intent.entities

        # Otopark Hesabı Tetikleme
        if ent.unit_count is not None and (user_intent.intent in ["PARKING_CALC", "PROJECT_CHECK"] or "otopark" in user_intent.detected_topics):
            parking_inputs = {
                "unit_count": ent.unit_count,
                "existing_parking": ent.existing_parking or 0,
                "units_under_80": ent.units_under_80 or 0,
                "units_80_to_140": ent.units_80_to_140 or 0,
                "units_over_140": ent.units_over_140 or 0,
            }
            res = self.rule_engine.execute("rule:otopark:konut:v2022", parking_inputs)
            if res.success and res.trace:
                calc_traces.append(res.trace)
                interpretation = interpret_calculation(res.trace, project_name=ent.district)

        # Emsal / TAKS Hesabı Tetikleme
        if ent.parcel_area is not None and ent.kaks is not None:
            emsal_inputs = {
                "parcel_area": ent.parcel_area,
                "kaks": ent.kaks,
                "taks": ent.taks or 0.0,
                "proposed_gross_area": ent.proposed_gross_area or 0.0,
                "exempt_area": ent.exempt_area or 0.0,
            }
            res_emsal = self.rule_engine.execute("rule:imar:emsal_taks:v2026", emsal_inputs)
            if res_emsal.success and res_emsal.trace:
                calc_traces.append(res_emsal.trace)
                emsal_interp = interpret_calculation(res_emsal.trace, project_name=ent.district)
                if not interpretation:
                    interpretation = emsal_interp
                else:
                    # İki yorumu birleştir
                    interpretation.compliance_notes.extend(emsal_interp.compliance_notes)
                    interpretation.design_recommendations.extend(emsal_interp.design_recommendations)
                    interpretation.authority_warnings.extend(emsal_interp.authority_warnings)
                    interpretation.applicable_articles.extend(emsal_interp.applicable_articles)

        # 3. RETRIEVAL (Kanıt Toplama)
        filters = QueryFilter(jurisdiction=effective_jurisdiction, limit=limit)
        evidence_list = self.retrieval.retrieve(query, filters)

        # Eğer sorgu hesaplama tetiklediyse ve serbest metin FTS doğrudan kanıt bulamadıysa,
        # kuralın dayandığı resmi mevzuat maddelerini kanıt olarak getir
        if not evidence_list and calc_traces:
            for ct in calc_traces:
                rule_evidence = self.retrieval.retrieve(
                    ct.rule_name,
                    QueryFilter(document_id=ct.source_document, limit=limit),
                )
                if not rule_evidence:
                    # Dokümanın temel maddelerini çek
                    rule_evidence = self.retrieval.retrieve(
                        "Madde",
                        QueryFilter(document_id=ct.source_document, limit=limit),
                    )
                evidence_list.extend(rule_evidence)

        # 4. ANSWER COMPOSITION
        # Eğer hesaplama yapıldıysa ve yorum varsa, cevaba mimari değerlendirmeyi ekle
        validated_answer, val_result = self.composer.compose(query, evidence_list)

        if val_result.accepted and interpretation and validated_answer:
            # Doğrulanmış cevabın üstüne profesyonel mimari yorumu ekle
            interp_text = (
                f"\n\n🏗️ [MİMARİ DEĞERLENDİRME & UZMAN YORUMU]:\n"
                f"• Durum: {interpretation.verdict}\n"
                f"• Özet: {interpretation.summary}\n\n"
                f"📋 [Tasarım ve Çözüm Önerileri]:\n" +
                "\n".join(f"  • {rec}" for rec in interpretation.design_recommendations) + "\n\n" +
                f"⚠️ [Ruhsat & İdare Uyarıları]:\n" +
                "\n".join(f"  • {warn}" for warn in interpretation.authority_warnings)
            )
            # ValidatedAnswer body'sini zenginleştir (atıflar korunarak)
            validated_answer = ValidatedAnswer(
                body=validated_answer.body + interp_text,
                citations=validated_answer.citations,
                confidence=validated_answer.confidence,
                evidence_used=validated_answer.evidence_used,
            )

        duration_ms = (time.perf_counter() - t0) * 1000

        # 5. AUDIT LOG (DATA_MODEL.txt bölüm 7 answer tablosu)
        article_ids_json = json.dumps(
            [f"{e.document_id}:{e.article}" for e in validated_answer.evidence_used],
            ensure_ascii=False,
        )
        versions_json = json.dumps(
            {e.document_id: e.version for e in validated_answer.evidence_used},
            ensure_ascii=False,
        )
        calc_trace_id = calc_traces[0].trace_id if calc_traces else None

        self.conn.execute(
            """
            INSERT INTO answer (
                answer_id, query_text, resolved_context, retrieved_article_ids_json,
                source_versions_json, confidence_level, calculation_trace_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trace_id,
                query,
                effective_jurisdiction,
                article_ids_json,
                versions_json,
                validated_answer.confidence.value,
                calc_trace_id,
                now_iso,
            ),
        )
        self.conn.commit()

        return ExecutionTrace(
            trace_id=trace_id,
            query=query,
            jurisdiction=effective_jurisdiction,
            intent=user_intent,
            evidence_found=evidence_list,
            validated_answer=validated_answer,
            validation_result=val_result,
            calculation_traces=calc_traces,
            interpretation=interpretation,
            duration_ms=duration_ms,
            created_at=now_iso,
        )
