"""Citation Enforcer - ARCHITECTURE.txt bolum 2 ve RAG_DESIGN.txt
bolum 6'da tanimlanan, mimarinin en kritik guven bilesteni.

Kural: bir DraftAnswer'daki HER atif (madde/URL/versiyon), retrieval'in
gercekten dondurdugu Evidence listesiyle MEKANIK olarak (string/ID
eslestirme ile) dogrulanir. Bu dogrulama prompt disiplinine degil, bu
modulun kodunda cebirsel bir esitlik kontrolune dayanir - LLM'in
"uydurmasi" bu katmanda YAKALANMALI.

Bu modul kasitli olarak hicbir LLM/network cagrisi icermez: girdisi ve
ciktisi tamamen deterministiktir, boylece bagimsiz test edilebilir
(bkz. REPORT.txt "Recommended Next Tasks" madde 4).
"""

from __future__ import annotations

from .models import Citation, DraftAnswer, Evidence, ValidatedAnswer, ValidationResult


def _normalize(value: str | None) -> str | None:
    """'Madde 5' ile '5' ile ' madde5 ' ayni maddeyi isaret ediyorsa
    esit sayilmali - ama bu SADECE bicimsel normalizasyon, anlamsal
    yorum degil."""
    if value is None:
        return None
    v = value.strip().lower()
    v = v.replace("madde", "").replace(" ", "").replace(".", "")
    return v or None


def _evidence_key(e: Evidence) -> tuple[str, str | None, str | None]:
    return (e.document_id, _normalize(e.article), _normalize(e.paragraph))


def _citation_key(c: Citation) -> tuple[str, str | None, str | None]:
    return (c.document_id, _normalize(c.article), _normalize(c.paragraph))


def validate_citations(draft: DraftAnswer, evidence: list[Evidence]) -> ValidationResult:
    """Draft'taki her Citation'in evidence listesinde karsiligi var mi
    kontrol eder. Bos evidence veya atifsiz draft otomatik reddedilir
    (RAG_DESIGN.txt bolum 7: bos sonucta Answer Composer hic
    cagrilmamalidir - bu fonksiyon o kuralin ikinci savunma hatti)."""

    reasons: list[str] = []

    if not evidence:
        return ValidationResult(accepted=False, reasons=["no_evidence_provided"])

    if not draft.citations:
        return ValidationResult(accepted=False, reasons=["draft_has_no_citations"])

    evidence_by_doc_article: dict[tuple[str, str | None, str | None], list[Evidence]] = {}
    evidence_by_doc: dict[tuple[str, str | None], list[Evidence]] = {}
    for e in evidence:
        evidence_by_doc_article.setdefault(_evidence_key(e), []).append(e)
        evidence_by_doc.setdefault((e.document_id, _normalize(e.article)), []).append(e)

    for c in draft.citations:
        key = _citation_key(c)
        matches = evidence_by_doc_article.get(key)

        # Citation paragraf belirtmiyorsa, ayni madde altindaki herhangi
        # bir fikrayla eslesmesi yeterli (madde seviyesinde atif gecerli).
        if not matches and c.paragraph is None:
            matches = evidence_by_doc.get((c.document_id, _normalize(c.article)))

        if not matches:
            reasons.append(
                f"unmatched_citation: document_id={c.document_id} "
                f"article={c.article!r} paragraph={c.paragraph!r}"
            )
            continue

        if c.source_url and not any(m.source_url == c.source_url for m in matches):
            reasons.append(
                f"url_mismatch: document_id={c.document_id} article={c.article!r} "
                f"claimed_url={c.source_url!r}"
            )

        if c.version and not any(m.version == c.version for m in matches):
            reasons.append(
                f"version_mismatch: document_id={c.document_id} article={c.article!r} "
                f"claimed_version={c.version!r}"
            )

    return ValidationResult(accepted=len(reasons) == 0, reasons=reasons)


def enforce(
    draft: DraftAnswer, evidence: list[Evidence]
) -> tuple[ValidatedAnswer | None, ValidationResult]:
    """Ust seviye giris noktasi. Kabul edilirse ValidatedAnswer doner;
    reddedilirse (None, ValidationResult) doner ve caller
    REJECTION_MESSAGE veya duzeltme akisini kullanmalidir - reddedilen
    bir DraftAnswer.body ASLA dogrudan kullaniciya gosterilmemelidir."""

    result = validate_citations(draft, evidence)
    if not result.accepted:
        return None, result

    used_keys = {_citation_key(c) for c in draft.citations}
    evidence_used = [e for e in evidence if _evidence_key(e) in used_keys]

    validated = ValidatedAnswer(
        body=draft.body,
        citations=draft.citations,
        confidence=draft.confidence,
        evidence_used=evidence_used,
    )
    return validated, result
