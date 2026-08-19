"""Data model per DATA_MODEL.txt. Kept as plain dataclasses: no ORM
magic, so Citation Enforcer logic stays trivially auditable."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ConfidenceLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NEEDS_AUTHORITY_REVIEW = "NEEDS_AUTHORITY_REVIEW"


# Standart red mesaji - SOURCE_POLICY.txt bolum 5'te tanimlanan, birebir
# kullanilmasi gereken metin. Baska bir yerde yeniden yazilmamali.
REJECTION_MESSAGE = (
    "Yüklenen/güncel mevzuat setinde bu soruyu güvenilir biçimde "
    "cevaplayacak yeterli dayanak bulunamadı."
)


@dataclass(frozen=True)
class Evidence:
    """Retrieval'in urettigi, Answer Composer'a gecirilen tek kanit
    parcasi. DATA_MODEL.txt Article + Document'in ilgili alanlarinin
    retrieval anindaki izdusumu."""

    document_id: str
    article: str
    text: str
    source_url: str
    version: str
    jurisdiction: str = "TR"
    paragraph: Optional[str] = None
    subparagraph: Optional[str] = None
    retrieval_score: float = 0.0


@dataclass(frozen=True)
class Citation:
    """Answer Composer'in ürettigi taslak cevaptaki TEK BIR atif iddiasi.
    Bu, henuz dogrulanmamis bir IDDIADIR - Evidence ile eslesmeden
    kullaniciya gosterilmez."""

    document_id: str
    article: str
    paragraph: Optional[str] = None
    source_url: Optional[str] = None
    version: Optional[str] = None


@dataclass
class DraftAnswer:
    """Answer Composer (LLM) ciktisi - HENUZ dogrulanmamis, kullaniciya
    dogrudan gosterilmemesi gereken ara urun."""

    body: str
    citations: list[Citation] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.LOW


@dataclass
class ValidationResult:
    accepted: bool
    reasons: list[str] = field(default_factory=list)


@dataclass
class ValidatedAnswer:
    """Citation Enforcer'dan gecmis, kullaniciya gosterilmeye uygun
    cevap."""

    body: str
    citations: list[Citation]
    confidence: ConfidenceLevel
    evidence_used: list[Evidence]
