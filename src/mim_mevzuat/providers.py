"""LLM Provider Abstraction - ARCHITECTURE.txt bölüm 6 ve RAG_DESIGN.txt
ilkelerine uygun LLM sağlayıcı soyutlaması.

Sağlayıcılar:
- LLMProvider (Protocol / ABC): Temel arayüz.
- MockGroundedProvider: Çevrimdışı testler ve deterministik çalışma için
  yalnızca Evidence içeriğini özetleyen, uydurmasız sağlayıcı.
- GeminiProvider: Canlı API anahtarı ile çalışan Google Gemini sağlayıcısı.
"""

from __future__ import annotations

import json
import os
from typing import Optional, Protocol

from .models import Citation, ConfidenceLevel, DraftAnswer, Evidence


class LLMProvider(Protocol):
    """LLM Sağlayıcı arayüzü."""

    def generate_draft(self, query: str, evidence: list[Evidence]) -> DraftAnswer:
        """Sorgu ve kanıt paketini alıp doğrulanmamış bir DraftAnswer üretir."""
        ...


class MockGroundedProvider:
    """Testler, yerel prototip ve çevrimdışı çalışma için deterministik sağlayıcı.
    Evidence haricinde hiçbir dış bilgi kullanmaz; her zaman gerçek ve eşleşen
    Citation nesneleri üretir."""

    def __init__(self, simulate_hallucination: bool = False, fabricated_article: str = None):
        self.simulate_hallucination = simulate_hallucination
        self.fabricated_article = fabricated_article

    def generate_draft(self, query: str, evidence: list[Evidence]) -> DraftAnswer:
        if not evidence:
            return DraftAnswer(
                body="Yeterli kanıt bulunamadı.",
                citations=[],
                confidence=ConfidenceLevel.LOW,
            )

        citations: list[Citation] = []
        body_lines: list[str] = [
            f"'{query.strip()}' sorusuna ilişkin yürürlükteki mevzuat hükümleri aşağıda özetlenmiştir:\n"
        ]

        for idx, ev in enumerate(evidence, 1):
            ref_str = f"{ev.article}" + (f" fıkra {ev.paragraph}" if ev.paragraph else "")
            body_lines.append(f"{idx}. {ref_str}: {ev.text}")

            citations.append(
                Citation(
                    document_id=ev.document_id,
                    article=ev.article,
                    paragraph=ev.paragraph,
                    source_url=ev.source_url,
                    version=ev.version,
                )
            )

        # Red-team test simülasyonu: Kasıtlı olarak sahte/uydurma madde veya URL ekle
        if self.simulate_hallucination:
            fake_art = self.fabricated_article or "Madde 999"
            citations.append(
                Citation(
                    document_id=evidence[0].document_id,
                    article=fake_art,
                    source_url="https://uydurma-kaynak.gov.tr",
                    version="2099.01",
                )
            )
            body_lines.append(f"\n[Uydurma İddia]: {fake_art} hükmüne göre...")

        return DraftAnswer(
            body="\n".join(body_lines),
            citations=citations,
            confidence=ConfidenceLevel.HIGH,
        )


class GeminiProvider:
    """Google Gemini API kullanarak DraftAnswer üreten sağlayıcı."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self.model_name = model_name

    def generate_draft(self, query: str, evidence: list[Evidence]) -> DraftAnswer:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY bulunamadı. Canlı LLM çağrısı için API anahtarı gereklidir.")

        # Evidence paketini JSON olarak hazırla
        evidence_payload = [
            {
                "document_id": e.document_id,
                "article": e.article,
                "paragraph": e.paragraph,
                "text": e.text,
                "source_url": e.source_url,
                "version": e.version,
                "jurisdiction": e.jurisdiction,
            }
            for e in evidence
        ]

        system_instruction = (
            "Sen Türkiye mimari mevzuatında uzman, kesinlikle uydurma yapmayan bir asistansın.\n"
            "KURAL 1: YALNIZCA sana verilen KANIT (Evidence) listesindeki metinlere dayanarak cevap ver.\n"
            "KURAL 2: Kanıt listesinde olmayan hiçbir madde numarası, oran veya kural uydurma.\n"
            "KURAL 3: Cevabında kullandığın her kanıt için citations listesinde ilgili document_id, article, paragraph, source_url ve version bilgilerini birebir ver.\n"
            "Çıktıyı şu JSON formatında üret:\n"
            '{"body": "Doğal dille yazılmış açık ve net cevap", "citations": [{"document_id": "...", "article": "...", "paragraph": "...", "source_url": "...", "version": "..."}], "confidence": "HIGH"}'
        )

        user_content = (
            f"Kullanıcı Sorusu: {query}\n\n"
            f"Resmi Kanıtlar:\n{json.dumps(evidence_payload, ensure_ascii=False, indent=2)}"
        )

        try:
            import requests

            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
            payload = {
                "system_instruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"parts": [{"text": user_content}]}],
                "generationConfig": {"response_mime_type": "application/json"},
            }
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)

            citations = [
                Citation(
                    document_id=c.get("document_id", ""),
                    article=c.get("article", ""),
                    paragraph=c.get("paragraph"),
                    source_url=c.get("source_url"),
                    version=c.get("version"),
                )
                for c in parsed.get("citations", [])
            ]
            conf_str = parsed.get("confidence", "HIGH")
            try:
                conf = ConfidenceLevel(conf_str)
            except ValueError:
                conf = ConfidenceLevel.HIGH

            return DraftAnswer(
                body=parsed.get("body", ""),
                citations=citations,
                confidence=conf,
            )
        except Exception as e:
            return DraftAnswer(
                body=f"LLM çağrısı sırasında hata oluştu: {e}",
                citations=[],
                confidence=ConfidenceLevel.LOW,
            )
