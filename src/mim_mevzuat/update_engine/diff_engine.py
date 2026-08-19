"""Diff Engine - UPDATE_ENGINE.txt bölüm 2 ilkelerine uygun mevzuat diff motoru.

İki mevzuat versiyonu arasındaki farkları madde ve fıkra düzeyinde tespit eder:
- Yeni eklenen maddeler (EK MADDE / yeni fıkra)
- Değiştirilen hükümler (DEĞİŞİKLİK)
- Yürürlükten kalkan hükümler (MÜLGA)
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Optional

from ..ingestion.parser import ParsedArticle, ParsedDocument


@dataclass
class ArticleDiff:
    article: str
    change_type: str  # "ADDED", "MODIFIED", "REPEALED", "UNCHANGED"
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    diff_unified: Optional[str] = None


@dataclass
class LegislationDiffReport:
    document_title: str
    old_version: str
    new_version: str
    changes_count: int
    modified_articles: list[ArticleDiff] = field(default_factory=list)
    added_articles: list[ArticleDiff] = field(default_factory=list)
    repealed_articles: list[ArticleDiff] = field(default_factory=list)


def compare_documents(
    doc_title: str,
    old_doc: ParsedDocument,
    old_version: str,
    new_doc: ParsedDocument,
    new_version: str,
) -> LegislationDiffReport:
    """İki ayrıştırılmış mevzuat belgesini karşılaştırıp detaylı diff raporu üretir."""

    old_by_art: dict[str, list[ParsedArticle]] = {}
    for a in old_doc.articles:
        key = f"{a.article}" + (f":f{a.paragraph}" if a.paragraph else "")
        old_by_art.setdefault(key, []).append(a)

    new_by_art: dict[str, list[ParsedArticle]] = {}
    for a in new_doc.articles:
        key = f"{a.article}" + (f":f{a.paragraph}" if a.paragraph else "")
        new_by_art.setdefault(key, []).append(a)

    modified: list[ArticleDiff] = []
    added: list[ArticleDiff] = []
    repealed: list[ArticleDiff] = []

    all_keys = set(old_by_art.keys()) | set(new_by_art.keys())

    for key in sorted(all_keys):
        in_old = key in old_by_art
        in_new = key in new_by_art

        if in_new and not in_old:
            new_text = " ".join(a.text for a in new_by_art[key])
            added.append(
                ArticleDiff(
                    article=key,
                    change_type="ADDED",
                    old_text=None,
                    new_text=new_text,
                )
            )
        elif in_old and not in_new:
            old_text = " ".join(a.text for a in old_by_art[key])
            repealed.append(
                ArticleDiff(
                    article=key,
                    change_type="REPEALED",
                    old_text=old_text,
                    new_text=None,
                )
            )
        else:
            old_text = " ".join(a.text for a in old_by_art[key])
            new_text = " ".join(a.text for a in new_by_art[key])

            if old_text.strip() != new_text.strip():
                # Metin değişmiş
                diff_lines = list(
                    difflib.unified_diff(
                        old_text.splitlines(keepends=True),
                        new_text.splitlines(keepends=True),
                        fromfile=f"Eski (v:{old_version})",
                        tofile=f"Yeni (v:{new_version})",
                    )
                )
                unified_str = "".join(diff_lines) if diff_lines else f"- {old_text}\n+ {new_text}"
                modified.append(
                    ArticleDiff(
                        article=key,
                        change_type="MODIFIED",
                        old_text=old_text,
                        new_text=new_text,
                        diff_unified=unified_str,
                    )
                )

    total_changes = len(modified) + len(added) + len(repealed)
    return LegislationDiffReport(
        document_title=doc_title,
        old_version=old_version,
        new_version=new_version,
        changes_count=total_changes,
        modified_articles=modified,
        added_articles=added,
        repealed_articles=repealed,
    )
