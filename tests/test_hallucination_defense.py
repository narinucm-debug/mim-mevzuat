"""Hallucination Red-Team Testleri - TEST_STRATEGY.txt bölüm 1.

Sistemin en kritik başarı kriteri: Yanlış zeminde veya kanıtsız durumda
ASLA kesin cevap vermemek, uydurma madde numaralarını ve atıfları engellemek.
"""

from mim_mevzuat.assistant import MevzuatAssistant
from mim_mevzuat.models import ConfidenceLevel, REJECTION_MESSAGE
from mim_mevzuat.providers import MockGroundedProvider


def test_defense_nonexistent_article_number():
    """Senaryo 1: Sistemde OLMAYAN bir madde numarası sorulması (ör. Madde 47)."""
    assistant = MevzuatAssistant(db_path=":memory:")
    query = "Otopark Yönetmeliği madde 47'de ne yazıyor?"

    trace = assistant.ask(query)

    # Retrieval boş dönmeli veya olmayan madde uydurulmamalı
    assert len(trace.evidence_found) == 0
    assert REJECTION_MESSAGE in trace.validated_answer.body
    assert trace.validated_answer.confidence == ConfidenceLevel.LOW
    assert len(trace.validated_answer.citations) == 0


def test_defense_completely_out_of_scope_query():
    """Senaryo 2: Mevzuat kapsamı dışındaki bir konu sorulduğunda standart red mesajı dönmesi."""
    assistant = MevzuatAssistant(db_path=":memory:")
    query = "Kuantum fotonik lazer güdümlü nükleer füzyon motoru çalıştırma esasları"

    trace = assistant.ask(query)

    assert len(trace.evidence_found) == 0
    assert REJECTION_MESSAGE in trace.validated_answer.body
    assert trace.validation_result.accepted is False


def test_defense_simulated_llm_hallucinated_article_blocked():
    """Senaryo 3: LLM kasıtlı olarak uydurma bir madde atfı (ör. Madde 999) ürettiğinde
    CitationEnforcer'ın bunu yakalayıp cevabı engellemesi."""
    # Kasıtlı olarak halüsinasyon gören / uyduran bir provider tanımla
    faulty_provider = MockGroundedProvider(
        simulate_hallucination=True,
        fabricated_article="Madde 999",
    )
    assistant = MevzuatAssistant(db_path=":memory:", provider=faulty_provider)

    query = "Otopark hesabı nasıl yapılır?"
    trace = assistant.ask(query)

    # Retrieval kanıt bulmuş olsa bile LLM'in uydurma atfı nedeniyle Validation reddetmeli
    assert trace.validation_result.accepted is False
    assert any("unmatched_citation" in r for r in trace.validation_result.reasons)
    # Reddedilen uydurma metin kullanıcıya güvenli red mesajı olarak dönmeli
    assert "Atıf doğrulaması başarısız oldu" in trace.validated_answer.body


def test_defense_simulated_llm_fake_url_blocked():
    """Senaryo 4: LLM doğru madde numarası verse bile uydurma bir URL verdiğinde engellenmesi."""
    faulty_provider = MockGroundedProvider(
        simulate_hallucination=True,
        fabricated_article="Madde 1",  # Madde 1 var ama provider sahte URL ile 999 da ekliyor
    )
    assistant = MevzuatAssistant(db_path=":memory:", provider=faulty_provider)

    query = "Otopark Yönetmeliği amacı nedir?"
    trace = assistant.ask(query)

    assert trace.validation_result.accepted is False
    assert trace.validated_answer.confidence == ConfidenceLevel.LOW
