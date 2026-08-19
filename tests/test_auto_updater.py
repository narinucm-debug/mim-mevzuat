"""AutoUpdater testleri - Arka plan otomatik güncelleme ve Resmî Gazete denetimi."""

import sqlite3
from mim_mevzuat.db import apply_schema, connect
from mim_mevzuat.update_engine.auto_updater import AutoUpdater


def test_auto_updater_check():
    conn = connect(":memory:", check_same_thread=False)
    apply_schema(conn)

    updater = AutoUpdater(conn, check_interval_seconds=3600, auto_start=False)
    res = updater.run_update_check()

    assert res["success"] is True
    assert res["status"] == "GÜNCEL"
    assert "checked_at" in res

    # Veritabanı kaydı kontrolü
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM update_log")
    rows = cursor.fetchall()
    assert len(rows) >= 1

    status = updater.get_status()
    assert status["auto_update_enabled"] is True
