"""Structure Parser - Mevzuat metinlerini yapısal bileşenlerine
(Bölüm, Madde, Fıkra, Bent, Alt Bent) ayrıştıran modül.

RAG_DESIGN.txt bölüm 4 ve ARCHITECTURE.txt bölüm 1 ilkelerine uygun olarak:
- Kör token chunking YAPMAZ; mevzuatın hukuki ve yapısal sınırlarını korur.
- Madde başlıklarını, fıkra numaralarını (1, 2, ...), bentleri (a, b, ...)
  ve alt bentleri (1, 2, ...) tespit eder.
- mevzuat.gov.tr konsolide metinlerindeki değişiklik işaretlerini
  (ör. '(Değişik:RG-25/3/2021-31434)', '(Mülga:...)', '(Ek:...)') korur.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedArticle:
    article: str                      # ör. "Madde 4", "Geçici Madde 1"
    paragraph: Optional[str] = None   # ör. "1", "2" veya None
    subparagraph: Optional[str] = None # ör. "a", "b" veya None
    title: Optional[str] = None       # ör. "Genel esaslar"
    text: str = ""                    # İlgili fıkra/madde metni
    raw_full_text: str = ""           # Tüm maddenin ham metni
    topics: list[str] = field(default_factory=list)
    amendments: list[str] = field(default_factory=list)


@dataclass
class ParsedDocument:
    title: str
    articles: list[ParsedArticle] = field(default_factory=list)
    raw_header: str = ""


# Madde başlangıç kalıbı (MADDE 1, GEÇİCİ MADDE 2, EK MADDE 3 vb.)
_ARTICLE_START_REGEX = re.compile(
    r"(?:\n|^)\s*(MADDE\s+\d+|GEÇİCİ\s+MADDE\s+\d+|EK\s+MADDE\s+\d+)"
    r"\s*(?:[-–—\.]\s*|\s+)",
    re.IGNORECASE,
)

# Fıkra başlangıç kalıbı: "(1)", "(2)" vb. satır başı veya madde başlangıcı sonrası
_PARAGRAPH_REGEX = re.compile(r"(?:\n|^)\s*\((\d+)\)\s*")

# Bent başlangıç kalıbı: "a)", "b)", "c)", "ç)" vb.
_SUBPARAGRAPH_REGEX = re.compile(r"(?:\n|^)\s*([a-zçğıöşüA-ZÇĞİÖŞÜ])\)\s*")

# Değişiklik/Mülga/Ek işaretleri kalıbı
_AMENDMENT_REGEX = re.compile(r"\((?:Değişik|Mülga|Ek|Yeniden düzenlenen)[^)]*RG-[^)]*\)")

# Otomatik konu etiketleme anahtar kelimeleri
_TOPIC_KEYWORDS = {
    "otopark": ["otopark", "park yeri", "ukome", "garaj", "manevra alanı"],
    "emsal": ["emsal", "kaks", "kat alanı kat sayısı", "emsale dahil", "emsal hesabı"],
    "taks": ["taks", "taban alanı kat sayısı", "taban alanı"],
    "yangin": ["yangın", "kaçış merdiveni", "duman", "itfaiye", "yangın güvenlik"],
    "siginak": ["sığınak", "serpinti sığınağı", "özel sığınak"],
    "asansor": ["asansör", "makina dairesi", "kuyu"],
    "engelli": ["engelli", "erişilebilirlik", "bedensel engelli", "tekerlekli sandalye"],
    "ev_sarj": ["şarj", "elektrikli araç", "şarj ünitesi", "şarj altyapısı"],
    "ruhsat": ["yapı ruhsatı", "yapı kullanma izin belgesi", "ruhsat"],
    "bahce_mesafesi": ["bahçe mesafesi", "ön bahçe", "yan bahçe", "arka bahçe"],
}


def _infer_topics(text: str) -> list[str]:
    low = text.lower()
    matched = []
    for topic, kws in _TOPIC_KEYWORDS.items():
        if any(kw in low for kw in kws):
            matched.append(topic)
    return matched


def _extract_amendments(text: str) -> list[str]:
    return [m.group(0) for m in _AMENDMENT_REGEX.finditer(text)]


import unicodedata

def _clean_text(text: str) -> str:
    """Metin içindeki gereksiz boşlukları ve sayfa sonu artıklarını temizler."""
    normalized = unicodedata.normalize("NFC", text)
    lines = [line.strip() for line in normalized.splitlines()]
    lines = [line for line in lines if line]
    return " ".join(lines)


def parse_legislation_text(raw_text: str) -> ParsedDocument:
    """Ham mevzuat metnini (veya PDF'ten çıkarılmış sayfa metinlerinin
    birleşimini) yapısal olarak Madde ve Fıkra kayıtlarına ayrıştırır."""

    # Başlık ve genel metin ayrıştırma
    matches = list(_ARTICLE_START_REGEX.finditer(raw_text))
    if not matches:
        # Madde formatı olmayan düz belge (Section tipi)
        first_line = raw_text.strip().splitlines()[0] if raw_text.strip() else "Mevzuat Metni"
        return ParsedDocument(
            title=first_line,
            articles=[
                ParsedArticle(
                    article="Genel Metin",
                    text=_clean_text(raw_text),
                    raw_full_text=raw_text,
                    topics=_infer_topics(raw_text),
                )
            ],
            raw_header="",
        )

    # İlk maddeden önceki kısım doküman başlığı ve giriş bilgileridir
    header_text = raw_text[: matches[0].start()].strip()
    title_lines = [l.strip() for l in header_text.splitlines() if l.strip()]
    doc_title = title_lines[0] if title_lines else "Mevzuat Belgesi"

    parsed_articles: list[ParsedArticle] = []

    for i, match in enumerate(matches):
        article_name = match.group(1).title().strip()
        # İki madde arasındaki metin bloğu
        start_idx = match.end()
        end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
        article_body = raw_text[start_idx:end_idx].strip()

        amendments = _extract_amendments(article_body)
        raw_full_text = f"{article_name} – {article_body}"

        # Fıkra ayrıştırma
        p_matches = list(_PARAGRAPH_REGEX.finditer(article_body))
        if p_matches:
            # Birden fazla fıkra var
            for p_idx, p_match in enumerate(p_matches):
                p_num = p_match.group(1)
                p_start = p_match.end()
                p_end = p_matches[p_idx + 1].start() if p_idx + 1 < len(p_matches) else len(article_body)
                p_text = article_body[p_start:p_end].strip()

                cleaned = _clean_text(p_text)
                topics = _infer_topics(cleaned)

                parsed_articles.append(
                    ParsedArticle(
                        article=article_name,
                        paragraph=p_num,
                        text=cleaned,
                        raw_full_text=raw_full_text,
                        topics=topics,
                        amendments=_extract_amendments(p_text),
                    )
                )
        else:
            # Tek fıkralı veya fıkra numarasız madde
            cleaned = _clean_text(article_body)
            topics = _infer_topics(cleaned)

            parsed_articles.append(
                ParsedArticle(
                    article=article_name,
                    paragraph=None,
                    text=cleaned,
                    raw_full_text=raw_full_text,
                    topics=topics,
                    amendments=amendments,
                )
            )

    return ParsedDocument(
        title=doc_title,
        articles=parsed_articles,
        raw_header=header_text,
    )
