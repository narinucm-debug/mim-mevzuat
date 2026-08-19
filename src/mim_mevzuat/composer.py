"""Answer Composer - RAG_DESIGN.txt bölüm 6-7 ve ARCHITECTURE.txt
bölüm 2 ilkelerine uygun olarak Answer Generation ve Citation Enforcement
akışını yönetir.

İlkeler:
1. Pre-generation Gate: Eğer Retrieval hiç Evidence bulamazsa, Answer
   Composer/LLM HİÇ ÇAĞRILMAZ. Doğrudan REJECTION_MESSAGE döndürülür.
2. Post-generation Validation: LLM'in ürettiği DraftAnswer,
   CitationEnforcer ile mekanik olarak (Evidence listesiyle) doğrulanır.
   Eşleşmeyen en ufak bir atıf varsa taslak reddedilir ve kullanıcıya
   gösterilmez.
"""

from __future__ import annotations

from typing import Optional

from .citation_enforcer import enforce
from .models import (
    ConfidenceLevel,
    Evidence,
    REJECTION_MESSAGE,
    ValidatedAnswer,
    ValidationResult,
)
from .providers import LLMProvider, MockGroundedProvider


class AnswerComposer:
    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or MockGroundedProvider()

    def compose(
        self,
        query: str,
        evidence: list[Evidence],
    ) -> tuple[ValidatedAnswer, ValidationResult]:
        """Sorgu ve kanıtları alarak güvenli ve doğrulanmış cevap üretir."""

        # 1. Pre-generation Gate (RAG_DESIGN.txt bölüm 7)
        if not evidence:
            return (
                ValidatedAnswer(
                    body=REJECTION_MESSAGE,
                    citations=[],
                    confidence=ConfidenceLevel.LOW,
                    evidence_used=[],
                ),
                ValidationResult(accepted=False, reasons=["no_evidence_provided"]),
            )

        # 2. LLM / Provider Çağrısı
        draft = self.provider.generate_draft(query, evidence)

        # 3. Post-generation Citation Enforcement (ARCHITECTURE.txt bölüm 2)
        validated, result = enforce(draft, evidence)

        if not result.accepted or validated is None:
            # Doğrulanamayan taslak KESİNLİKLE kullanıcıya gösterilmez
            return (
                ValidatedAnswer(
                    body=REJECTION_MESSAGE + f"\n(Güvenlik Nedeni: Atıf doğrulaması başarısız oldu: {', '.join(result.reasons)})",
                    citations=[],
                    confidence=ConfidenceLevel.LOW,
                    evidence_used=[],
                ),
                result,
            )

        return validated, result
