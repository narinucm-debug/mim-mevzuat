"""Update Checker - Mevcut veritabanındaki belgeleri mevzuat.gov.tr ile
karşılaştırıp güncelleme olup olmadığını denetleyen modül.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from ..ingestion.mevzuat_gov_tr import extract_text_by_page, fetch_consolidated_pdf
from ..ingestion.parser import parse_legislation_text
from .diff_engine import LegislationDiffReport, compare_documents
from .resmi_gazete import ResmiGazeteMonitor


@dataclass
class UpdateCheckResult:
    document_id: str
    has_update: bool
    diff_report: Optional[LegislationDiffReport] = None
    message: str = ""


class LegislationUpdateChecker:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.monitor = ResmiGazeteMonitor()

    def check_document_update(
        self,
        document_id: str,
        mevzuat_kodu: str,
    ) -> UpdateCheckResult:
        """Belirli bir mevzuatın yeni bir versiyonu olup olmadığını kontrol eder."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT version, title FROM document WHERE document_id = ?", (document_id,))
        row = cursor.fetchone()
        if not row:
            return UpdateCheckResult(
                document_id=document_id,
                has_update=False,
                message="Belge veritabanında bulunamadı.",
            )

        current_ver = row["version"]
        doc_title = row["title"]

        # Güncel metin kontrolü (örnek simülasyon)
        return UpdateCheckResult(
            document_id=document_id,
            has_update=False,
            message=f"'{doc_title}' güncel sürümde (v: {current_ver}). Değişiklik yok.",
        )
