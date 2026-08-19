"""Citation Enforcer testleri. Bunlar TEST_STRATEGY.txt'nin "citation
validation'in (Evidence eslestirme) birim testi: kasitli olarak
'uydurma' bir madde iceren sahte LLM ciktisi verilip sistemin bunu
YAKALADIGI dogrulanir" maddesinin ilk somutlasmasidir (Faz 1.10)."""

from mim_mevzuat.citation_enforcer import enforce, validate_citations
from mim_mevzuat.models import Citation, ConfidenceLevel, DraftAnswer, Evidence

OTOPARK_EVIDENCE = Evidence(
    document_id="otopark-yonetmeligi",
    article="5",
    paragraph="1",
    text="Yapılacak binalarda otopark ihtiyacının bina içinde veya "
    "parselinde karşılanması esastır.",
    source_url="https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=24408&MevzuatTur=7&MevzuatTertip=5",
    version="2026.01",
    jurisdiction="TR",
)


def test_matching_citation_is_accepted():
    draft = DraftAnswer(
        body="Otopark ihtiyacı esas olarak parsel/bina içinde karşılanır.",
        citations=[Citation(document_id="otopark-yonetmeligi", article="5", paragraph="1")],
        confidence=ConfidenceLevel.HIGH,
    )

    validated, result = enforce(draft, [OTOPARK_EVIDENCE])

    assert result.accepted is True
    assert validated is not None
    assert validated.evidence_used == [OTOPARK_EVIDENCE]


def test_article_level_citation_matches_any_paragraph():
    """Citation paragraf belirtmezse (sadece madde bazinda atif), ayni
    maddenin herhangi bir fikrasiyla eslesmesi kabul edilmeli."""
    draft = DraftAnswer(
        body="Madde 5 otopark esaslarini duzenler.",
        citations=[Citation(document_id="otopark-yonetmeligi", article="5")],
        confidence=ConfidenceLevel.MEDIUM,
    )

    validated, result = enforce(draft, [OTOPARK_EVIDENCE])

    assert result.accepted is True
    assert validated is not None


def test_fabricated_article_number_is_rejected():
    """Cekirdek hallucination-defense testi: LLM sistemde OLMAYAN bir
    madde numarasi uydurursa, Citation Enforcer bunu YAKALAMALI."""
    draft = DraftAnswer(
        body="Madde 47'ye göre otopark oranı %10'dur.",
        citations=[Citation(document_id="otopark-yonetmeligi", article="47")],
        confidence=ConfidenceLevel.HIGH,
    )

    validated, result = enforce(draft, [OTOPARK_EVIDENCE])

    assert result.accepted is False
    assert validated is None
    assert any("unmatched_citation" in r for r in result.reasons)


def test_fabricated_url_is_rejected_even_if_article_matches():
    """Madde numarasi dogru olsa bile, atifin URL'i evidence'taki
    gercek URL ile eslesmiyorsa reddedilmeli (URL uydurulamaz kurali,
    bkz. SOURCE_POLICY.txt madde 3)."""
    draft = DraftAnswer(
        body="Kaynak: uydurma-site.com/otopark",
        citations=[
            Citation(
                document_id="otopark-yonetmeligi",
                article="5",
                paragraph="1",
                source_url="https://uydurma-site.com/otopark",
            )
        ],
        confidence=ConfidenceLevel.HIGH,
    )

    validated, result = enforce(draft, [OTOPARK_EVIDENCE])

    assert result.accepted is False
    assert any("url_mismatch" in r for r in result.reasons)


def test_empty_evidence_rejects_regardless_of_draft():
    """Retrieval hicbir sey bulamadiysa, Answer Composer normalde hic
    cagrilmamali (RAG_DESIGN.txt bolum 7); ama bu fonksiyon bagimsiz
    bir ikinci savunma hatti olarak da bos evidence'i reddeder."""
    draft = DraftAnswer(
        body="Otopark oranı %20'dir.",
        citations=[Citation(document_id="otopark-yonetmeligi", article="5")],
        confidence=ConfidenceLevel.HIGH,
    )

    validated, result = enforce(draft, [])

    assert result.accepted is False
    assert validated is None
    assert result.reasons == ["no_evidence_provided"]


def test_draft_without_any_citation_is_rejected():
    """Atifsiz normatif cevap da reddedilmeli - kaynaksiz kesin ifade
    HALLUCINATION_DEFENSE kural 1'in ihlalidir."""
    draft = DraftAnswer(body="Otopark oranı %20'dir.", citations=[])

    validated, result = enforce(draft, [OTOPARK_EVIDENCE])

    assert result.accepted is False
    assert result.reasons == ["draft_has_no_citations"]


def test_superseded_document_citation_still_matches_mechanically():
    """Citation Enforcer SADECE Evidence ile string/ID eslestirmesi
    yapar; bir maddenin ACTIVE/SUPERSEDED olup olmadigini bilmez - bu
    kontrol Retrieval Orchestrator'in sorumlulugundadir (sadece guncel
    validity_status='ACTIVE' kayitlari Evidence olarak sunmali). Bu
    test, sorumluluk sinirinin net oldugunu belgeler."""
    stale_evidence = Evidence(
        document_id="otopark-yonetmeligi",
        article="5",
        paragraph="1",
        text="[eski versiyon metni]",
        source_url=OTOPARK_EVIDENCE.source_url,
        version="2019.01",
    )
    draft = DraftAnswer(
        body="...",
        citations=[
            Citation(
                document_id="otopark-yonetmeligi",
                article="5",
                paragraph="1",
                version="2019.01",
            )
        ],
    )

    result = validate_citations(draft, [stale_evidence])

    # Mekanik olarak eslesir (bu katmanin isi budur); guncellik kontrolu
    # Retrieval Orchestrator'da yapilmalidir - bkz. yorum.
    assert result.accepted is True
