"""3 Demo Sorusu Regresyon Testleri - PLAN.txt bölüm 6 çıkış kriteri.

Sistem şu 3 soruyu, her seferinde kaynak zincirini (SOURCE -> RETRIEVAL ->
ANSWER -> CITATION) görünür ve doğrulanmış kılarak cevaplayabilmelidir:
  1. "Bir alanın emsale dahil olup olmadığını nasıl kontrol etmeliyim?"
  2. "Konut projesinde otopark ihtiyacını hesaplamak için hangi bilgiler gerekli?"
  3. "Bu sorunun cevabını hangi resmi mevzuat maddesine dayandırıyorsun?"
"""

from mim_mevzuat.assistant import MevzuatAssistant
from mim_mevzuat.models import ConfidenceLevel


def test_demo_question_1_emsal_kontrolu():
    """Demo Soru 1: Bir alanın emsale dahil olup olmadığını nasıl kontrol etmeliyim?"""
    assistant = MevzuatAssistant(db_path=":memory:")
    query = "Bir alanın emsale dahil olup olmadığını nasıl kontrol etmeliyim?"

    trace = assistant.ask(query)

    # 1. RETRIEVAL doğrulaması
    assert len(trace.evidence_found) > 0
    doc_ids = {e.document_id for e in trace.evidence_found}
    assert "yonetmelik:7.5.23722" in doc_ids  # Planlı Alanlar İmar Yönetmeliği

    # 2. ANSWER & CITATION doğrulaması
    assert trace.validation_result.accepted is True
    assert trace.validated_answer.confidence in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]
    assert len(trace.validated_answer.citations) > 0

    # Atıflarda emsal maddesi (Madde 4, 5 veya 22) yer almalı
    articles = [c.article.lower() for c in trace.validated_answer.citations]
    assert any("madde 4" in a or "madde 5" in a or "madde 22" in a for a in articles)

    # Cevap metninde emsal ve mevzuat atfı yer almalı
    assert "emsal" in trace.validated_answer.body.lower()


def test_demo_question_2_otopark_ihtiyaci_bilgileri():
    """Demo Soru 2: Konut projesinde otopark ihtiyacını hesaplamak için hangi bilgiler gerekli?"""
    assistant = MevzuatAssistant(db_path=":memory:")
    query = "Konut projesinde otopark ihtiyacını hesaplamak için hangi bilgiler gerekli?"

    trace = assistant.ask(query)

    # 1. RETRIEVAL doğrulaması
    assert len(trace.evidence_found) > 0
    doc_ids = {e.document_id for e in trace.evidence_found}
    assert "yonetmelik:7.5.24408" in doc_ids  # Otopark Yönetmeliği

    # 2. ANSWER & CITATION doğrulaması
    assert trace.validation_result.accepted is True
    assert len(trace.validated_answer.citations) > 0

    # Otopark yönetmeliği atfı bulunmalı
    otopark_cits = [c for c in trace.validated_answer.citations if c.document_id == "yonetmelik:7.5.24408"]
    assert len(otopark_cits) > 0
    assert otopark_cits[0].source_url.startswith("https://www.mevzuat.gov.tr")

    # Cevap gövdesinde otopark metni yer almalı
    assert "otopark" in trace.validated_answer.body.lower()


def test_demo_question_3_dayanak_mevzuat_maddesi():
    """Demo Soru 3: Bu sorunun cevabını hangi resmi mevzuat maddesine dayandırıyorsun?"""
    assistant = MevzuatAssistant(db_path=":memory:")
    query = "Otopark Yönetmeliği genel esaslar ve parselde otopark düzeni hangi maddede yer alır?"

    trace = assistant.ask(query)

    assert trace.validation_result.accepted is True
    assert len(trace.evidence_found) > 0

    # Madde 4 veya Madde 5 tespit edilmeli
    articles = [e.article.lower() for e in trace.evidence_found]
    assert any("madde 4" in a or "madde 5" in a for a in articles)

    # Atıfta versiyon ve resmi kaynak URL tam olmalı
    for cit in trace.validated_answer.citations:
        assert cit.source_url is not None
        assert "mevzuat.gov.tr" in cit.source_url
        assert cit.version is not None
