"""MİM MEVZUAT - Komut Satırı Arayüzü (CLI).

Kullanım:
  python -m mim_mevzuat.cli ask "Konut projesinde otopark hesabı için hangi bilgiler gerekli?"
  python -m mim_mevzuat.cli trace "Bir alanın emsale dahil olup olmadığını nasıl kontrol etmeliyim?"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .assistant import MevzuatAssistant


def format_trace_output(trace) -> str:
    out = []
    out.append("=" * 70)
    out.append(f"SORU: {trace.query}")
    out.append(f"KAPSAM (JURISDICTION): {trace.jurisdiction}")
    out.append(f"SÜRE: {trace.duration_ms:.2f} ms | GÜVEN: {trace.validated_answer.confidence.value}")
    out.append("=" * 70)

    out.append("\n[1. RETRIEVAL - BULUNAN RESMİ KANITLAR]:")
    if not trace.evidence_found:
        out.append("  (Kanıt bulunamadı)")
    else:
        for idx, ev in enumerate(trace.evidence_found, 1):
            p_info = f" Fıkra {ev.paragraph}" if ev.paragraph else ""
            out.append(f"  [{idx}] {ev.document_id} -> {ev.article}{p_info}")
            out.append(f"      Kaynak URL: {ev.source_url}")
            out.append(f"      Yürürlük Versiyonu: {ev.version}")
            out.append(f"      Pasaj: {ev.text[:120]}...")

    if trace.calculation_traces:
        out.append("\n[1.5. RULE ENGINE - HESAPLAMA ÇIKTILARI]:")
        for ct in trace.calculation_traces:
            out.append(f"  • Kural: {ct.rule_name} ({ct.rule_id})")
            out.append(f"    Girdiler: {ct.inputs}")
            out.append(f"    Sonuç: {ct.result}")

    out.append("\n[2. ANSWER - DOĞRULANMIŞ CEVAP VE MİMARİ YORUM]:")
    out.append(trace.validated_answer.body)

    out.append("\n[3. CITATION ENFORCEMENT - ATIF KONTROLÜ]:")
    if trace.validation_result.accepted:
        out.append("  DURUM: KABUL EDİLDİ (Tüm atıflar kanıtlarla mekanik olarak eşleşti)")
        for c in trace.validated_answer.citations:
            p_str = f" fıkra {c.paragraph}" if c.paragraph else ""
            out.append(f"  - {c.document_id} :: {c.article}{p_str} (v: {c.version})")
    else:
        out.append(f"  DURUM: REDDEDİLDİ (Nedenler: {trace.validation_result.reasons})")

    out.append("=" * 70)
    return "\n".join(out)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="MİM MEVZUAT - Mimarlık Mevzuat Asistanı")
    subparsers = parser.add_subparsers(dest="command", help="Komutlar")

    # Ask komutu
    ask_parser = subparsers.add_parser("ask", help="Mevzuat sorusu sor")
    ask_parser.add_argument("query", type=str, help="Sorulacak soru")
    ask_parser.add_argument("--jurisdiction", type=str, default="TR", help="Yerel idare (ör. TR.Ankara.Cankaya)")

    # Trace komutu
    trace_parser = subparsers.add_parser("trace", help="SOURCE -> RETRIEVAL -> ANSWER -> CITATION iziyle sor")
    trace_parser.add_argument("query", type=str, help="Sorulacak soru")
    trace_parser.add_argument("--jurisdiction", type=str, default="TR", help="Yerel idare")

    # Serve komutu (Web UI)
    serve_parser = subparsers.add_parser("serve", help="Web uygulamasını başlat (FastAPI)")
    serve_parser.add_argument("--host", type=str, default="127.0.0.1", help="Sunucu host adresi")
    serve_parser.add_argument("--port", type=int, default=8000, help="Sunucu portu")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "serve":
        from .web.app import run_server
        print(f"🚀 MİM MEVZUAT Web Uygulaması Başlatılıyor: http://{args.host}:{args.port}")
        run_server(host=args.host, port=args.port)
        return

    assistant = MevzuatAssistant()

    if args.command in ["ask", "trace"]:
        trace = assistant.ask(args.query, jurisdiction=args.jurisdiction)
        print(format_trace_output(trace))


if __name__ == "__main__":
    main()
