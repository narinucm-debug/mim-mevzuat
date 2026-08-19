"""MİM MEVZUAT - Tek Tıkla .EXE Oluşturma Scripti (PyInstaller).

Bu scripti çalıştırdığınızda `dist/MimMevzuat.exe` adında tek dosya halinde
kurulumsuz ve taşınabilir bir Windows masaüstü uygulaması üretir.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()


def build():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("[*] MIM MEVZUAT Windows .EXE Derleme Islemi Baslatiliyor...\n")

    entrypoint = ROOT_DIR / "src" / "mim_mevzuat" / "desktop.py"
    schema_file = ROOT_DIR / "src" / "mim_mevzuat" / "schema.sql"
    fixtures_dir = ROOT_DIR / "tests" / "fixtures"
    certs_dir = ROOT_DIR / "src" / "mim_mevzuat" / "ingestion" / "certs"

    # PyInstaller parametreleri
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=MimMevzuat",
        "--onefile",
        "--windowed",
        "--clean",
        "--noconfirm",
        f"--add-data={schema_file};mim_mevzuat",
        f"--add-data={certs_dir};mim_mevzuat/ingestion/certs",
        f"--add-data={fixtures_dir};tests/fixtures",
        "--hidden-import=uvicorn",
        "--hidden-import=fastapi",
        "--hidden-import=pymupdf",
        "--hidden-import=fitz",
        "--hidden-import=sqlite3",
        "--hidden-import=starlette",
        "--hidden-import=anyio",
        "--hidden-import=webview",
        "--hidden-import=pythonnet",
        "--hidden-import=clr_loader",
        "--hidden-import=bottle",
        "--hidden-import=proxy_tools",
        "--paths=src",
        str(entrypoint),
    ]

    print("Çalıştırılan komut:")
    print(" ".join(cmd))
    print("\nLütfen bekleyin, Python kütüphaneleri ve mevzuat veritabanı tek bir .exe içine paketleniyor...\n")

    result = subprocess.run(cmd, cwd=str(ROOT_DIR))

    if result.returncode == 0:
        exe_path = ROOT_DIR / "dist" / "MimMevzuat.exe"
        print("\n" + "=" * 65)
        print("[SUCCESS] .EXE BASARIYLA OLUSTURULDU!")
        print("=" * 65)
        print(f"[+] Dosya Konumu: {exe_path}")
        print("[+] Bu .exe dosyasini dilediginiz Windows bilgisayara kopyalayip")
        print("    cift tiklayarak dogrudan calistirabilirsiniz (Python kurulumu gerekmez)!")
        print("=" * 65 + "\n")
    else:
        print(f"\n[-] Derleme sirasinda hata olustu. Cikis kodu: {result.returncode}")


if __name__ == "__main__":
    build()
