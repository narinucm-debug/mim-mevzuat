"""MİM MEVZUAT - Tek Tıkla Çalışan Masaüstü Giriş Noktası (.exe entrypoint).

Çift tıklandığında:
1. Yerel FastAPI sunucusunu arka planda başlatır.
2. Kullanıcının varsayılan tarayıcısında MİM MEVZUAT arayüzünü otomatik açar.
3. Çevrimdışı ve tam fonksiyonel olarak çalışır.
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
import webbrowser

import uvicorn

from mim_mevzuat.web.app import app


def _find_free_port(default_port: int = 8000) -> int:
    """Belirtilen port doluysa bir sonraki boş portu bulur."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", default_port))
        sock.close()
        return default_port
    except OSError:
        # Boş bir port ata
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    port = _find_free_port(8000)
    url = f"http://127.0.0.1:{port}"

    print("=" * 65)
    print("      MİM MEVZUAT — Mimarlık Mevzuat & Yorumlama Asistanı")
    print("      Masaüstü Sürümü Başlatılıyor...")
    print("=" * 65)
    print(f"\n[+] Yerel Sunucu Adresi: {url}")
    print("[+] Tarayıcınız otomatik olarak açılıyor...")
    print("[!] Çıkmak için bu pencereyi kapatabilir veya Ctrl + C yapabilirsiniz.\n")

    # Tarayıcıyı 1 saniye sonra aç
    def open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=open_browser, daemon=True).start()

    # Uvicorn sunucusunu ana thread'de çalıştır
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
