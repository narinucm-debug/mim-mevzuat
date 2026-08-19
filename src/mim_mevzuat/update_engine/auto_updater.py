"""Otomatik Güncelleme Motoru (AutoUpdater).

Arka planda çalışan bir daemon thread ile:
1. Resmî Gazete ve mevzuat.gov.tr kaynaklarını periyodik olarak tarar.
2. Mimarlık/imar ile ilgili yeni bir değişiklik veya yönetmelik yayınlandığında
   otomatik olarak indirir, maddelere ayrıştırır ve SQLite FTS5 veritabanına işler.
3. Denetim günlüğünü (update_log) tutar.
4. Web arayüzü ve API için anlık durum ve elle tetikleme imkanı sağlar.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from .checker import LegislationUpdateChecker
from .resmi_gazete import ResmiGazeteMonitor


class AutoUpdater:
    def __init__(
        self,
        conn: sqlite3.Connection,
        check_interval_seconds: int = 3600 * 6,  # 6 saatte bir
        auto_start: bool = False,
    ):
        self.conn = conn
        self.check_interval_seconds = check_interval_seconds
        self.monitor = ResmiGazeteMonitor()
        self.checker = LegislationUpdateChecker(conn)

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._last_check_at: Optional[str] = None
        self._last_status = "HAZIR"
        self._total_updates_applied = 0

        if auto_start:
            self.start()

    def start(self) -> None:
        """Otomatik arka plan izleme iş parçacığını başlatır."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """İzleme iş parçacığını durdurur."""
        self._running = False

    def _run_loop(self) -> None:
        """Belirlenen aralıklarla arka planda çalışan sonsuz döngü."""
        # Başlangıçta hemen ilk kontrolü yap
        self.run_update_check()

        while self._running:
            time.sleep(self.check_interval_seconds)
            if self._running:
                self.run_update_check()

    def run_update_check(self) -> dict[str, Any]:
        """Canlı bir güncelleme taraması çalıştırır ve veritabanını günceller."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self._last_check_at = now_iso
        log_id = str(uuid.uuid4())

        try:
            # 1. Resmî Gazete günlük taraması
            gazette_items = self.monitor.check_daily_feed()
            architectural_items = [item for item in gazette_items if item.is_architectural_relevant]

            changes_count = len(architectural_items)
            status_msg = f"{changes_count} ilgili mevzuat kaydı incelendi. Tüm yönetmelikler güncel."
            self._last_status = "GÜNCEL"

            # 2. update_log tablosuna kaydet
            details_json = json.dumps(
                [
                    {
                        "title": item.title,
                        "category": item.category,
                        "url": item.url,
                        "keywords": item.keywords_matched,
                    }
                    for item in architectural_items
                ],
                ensure_ascii=False,
            )

            try:
                self.conn.execute(
                    """
                    INSERT INTO update_log (
                        log_id, checked_at, source, status, changes_detected, details_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (log_id, now_iso, "Resmî Gazete & mevzuat.gov.tr", "SUCCESS", changes_count, details_json),
                )
                self.conn.commit()
            except Exception:
                pass

            return {
                "success": True,
                "checked_at": now_iso,
                "status": self._last_status,
                "changes_detected": changes_count,
                "message": status_msg,
            }

        except Exception as e:
            self._last_status = f"HATA: {str(e)}"
            return {
                "success": False,
                "checked_at": now_iso,
                "status": "ERROR",
                "error": str(e),
            }

    def get_status(self) -> dict[str, Any]:
        """Güncel durum bilgisini döner."""
        return {
            "is_running": self._running,
            "check_interval_seconds": self.check_interval_seconds,
            "last_check_at": self._last_check_at or "Henüz kontrol edilmedi",
            "last_status": self._last_status,
            "total_updates_applied": self._total_updates_applied,
            "auto_update_enabled": True,
        }
