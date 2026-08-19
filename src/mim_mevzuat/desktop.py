"""MİM MEVZUAT - Gerçek Yerel Masaüstü Uygulaması (Native Desktop Window).

Tarayıcı açmaz; doğrudan bağımsız bir masaüstü penceresi (Native GUI Window) olarak çalışır.
"""

from __future__ import annotations

import socket
import sys
import threading
import time
import uvicorn
import webview

from mim_mevzuat.web.app import app


def _find_free_port(default_port: int = 8000) -> int:
    """Belirtilen port doluysa boş bir port bulur."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", default_port))
        sock.close()
        return default_port
    except OSError:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        return port


def _start_server(port: int):
    """Uvicorn sunucusunu arka plan iş parçacığında çalıştırır."""
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    server.run()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    port = _find_free_port(8000)
    url = f"http://127.0.0.1:{port}"

    # Arka planda sunucuyu başlat
    server_thread = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server_thread.start()

    # Sunucunun hazır olması için kısa bir bekleme
    time.sleep(0.6)

    # Doğrudan Native Masaüstü Penceresini Oluştur (Tarayıcı gerektirmez)
    window = webview.create_window(
        title="MİM MEVZUAT — Mimari Mevzuat & Yorumlama Asistanı",
        url=url,
        width=1280,
        height=860,
        min_size=(960, 640),
        text_select=True,
        confirm_close=False,
    )

    # GUI penceresini başlat
    webview.start(private_mode=False)


if __name__ == "__main__":
    main()
