"""MİM MEVZUAT - Web Uygulaması ve REST API (FastAPI).

Doğal dil anlama (NLU), Hesap Motoru (Rule Engine), Mimari Yorumlama (Interpreter)
ve Citation Enforcement destekli tam teşekküllü web uygulaması.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..assistant import MevzuatAssistant
from ..ingestion.pipeline import DocumentMetadata, ingest_text
from ..interpreter import interpret_calculation
from ..update_engine.auto_updater import AutoUpdater

app = FastAPI(
    title="MİM MEVZUAT",
    description="Türkiye Mimari Mevzuat & Yorumlama Asistanı",
    version="0.0.3",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assistant = MevzuatAssistant()
updater = AutoUpdater(assistant.conn, auto_start=True)


class AskRequest(BaseModel):
    query: str
    jurisdiction: Optional[str] = None
    limit: int = 5


class CalculateRequest(BaseModel):
    rule_id: str
    inputs: dict[str, Any]
    project_name: Optional[str] = None


@app.post("/api/ask")
def api_ask(req: AskRequest):
    """Sorguyu NLU ile analiz eder, hesaplar, kanıtları çeker ve mimari yorumla döner."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Soru boş olamaz.")

    trace = assistant.ask(req.query, jurisdiction=req.jurisdiction, limit=req.limit)

    interp_data = None
    if trace.interpretation:
        interp_data = {
            "verdict": trace.interpretation.verdict,
            "summary": trace.interpretation.summary,
            "compliance_notes": trace.interpretation.compliance_notes,
            "design_recommendations": trace.interpretation.design_recommendations,
            "authority_warnings": trace.interpretation.authority_warnings,
            "applicable_articles": trace.interpretation.applicable_articles,
        }

    return {
        "trace_id": trace.trace_id,
        "query": trace.query,
        "jurisdiction": trace.jurisdiction,
        "duration_ms": round(trace.duration_ms, 2),
        "created_at": trace.created_at,
        "intent": {
            "type": trace.intent.intent if trace.intent else "QA",
            "topics": trace.intent.detected_topics if trace.intent else [],
        },
        "answer": {
            "body": trace.validated_answer.body,
            "confidence": trace.validated_answer.confidence.value,
            "citations": [
                {
                    "document_id": c.document_id,
                    "article": c.article,
                    "paragraph": c.paragraph,
                    "source_url": c.source_url,
                    "version": c.version,
                }
                for c in trace.validated_answer.citations
            ],
        },
        "validation": {
            "accepted": trace.validation_result.accepted,
            "reasons": trace.validation_result.reasons,
        },
        "calculation_traces": [
            {
                "rule_id": ct.rule_id,
                "rule_name": ct.rule_name,
                "inputs": ct.inputs,
                "method": ct.method,
                "result": ct.result,
                "source_document": ct.source_document,
                "source_article": ct.source_article,
                "confidence": ct.confidence.value,
            }
            for ct in trace.calculation_traces
        ],
        "interpretation": interp_data,
        "evidence": [
            {
                "document_id": e.document_id,
                "article": e.article,
                "paragraph": e.paragraph,
                "subparagraph": e.subparagraph,
                "text": e.text,
                "source_url": e.source_url,
                "version": e.version,
                "jurisdiction": e.jurisdiction,
                "retrieval_score": round(e.retrieval_score, 4),
            }
            for e in trace.evidence_found
        ],
    }


@app.get("/api/rules")
def api_list_rules():
    """Kullanılabilir rule pack listesini döner."""
    return {"rules": assistant.rule_engine.list_rules()}


@app.post("/api/calculate")
def api_calculate(req: CalculateRequest):
    """Doğrudan rule pack çalıştırır ve mimari yorum üretir."""
    res = assistant.rule_engine.execute(req.rule_id, req.inputs)
    if not res.success or not res.trace:
        raise HTTPException(
            status_code=400,
            detail=res.error_message or "Hesaplama gerçekleştirilemedi.",
        )

    interp = interpret_calculation(res.trace, project_name=req.project_name)
    return {
        "trace": {
            "trace_id": res.trace.trace_id,
            "rule_id": res.trace.rule_id,
            "rule_name": res.trace.rule_name,
            "inputs": res.trace.inputs,
            "method": res.trace.method,
            "result": res.trace.result,
            "source_document": res.trace.source_document,
            "source_article": res.trace.source_article,
            "confidence": res.trace.confidence.value,
        },
        "interpretation": {
            "verdict": interp.verdict,
            "summary": interp.summary,
            "compliance_notes": interp.compliance_notes,
            "design_recommendations": interp.design_recommendations,
            "authority_warnings": interp.authority_warnings,
            "applicable_articles": interp.applicable_articles,
        },
    }


@app.get("/api/documents")
def api_get_documents():
    """Sistemde yüklü olan mevzuat belgelerini listeler."""
    cursor = assistant.conn.cursor()
    cursor.execute(
        """
        SELECT d.document_id, d.title, d.authority, d.document_type,
               d.jurisdiction, d.version, d.source_url, d.validity_status,
               d.topics, COUNT(a.article_id) as article_count
        FROM document d
        LEFT JOIN article a ON a.document_id = d.document_id
        GROUP BY d.document_id
        ORDER BY d.title ASC
        """
    )
    rows = cursor.fetchall()
    docs = []
    for r in rows:
        topics = []
        try:
            topics = json.loads(r["topics"])
        except Exception:
            pass
        docs.append(
            {
                "document_id": r["document_id"],
                "title": r["title"],
                "authority": r["authority"],
                "document_type": r["document_type"],
                "jurisdiction": r["jurisdiction"],
                "version": r["version"],
                "source_url": r["source_url"],
                "validity_status": r["validity_status"],
                "topics": topics,
                "article_count": r["article_count"],
            }
        )
    return {"documents": docs}


@app.get("/api/updates/status")
def api_update_status():
    """Otomatik güncelleme motorunun canlı durumunu döner."""
    return updater.get_status()


@app.post("/api/updates/sync")
def api_trigger_update_sync():
    """Canlı güncelleme kontrolünü anında tetikler."""
    res = updater.run_update_check()
    return res


# Web Arayüzü HTML Sayfası (Single Page App)
INDEX_HTML = """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MİM MEVZUAT — Mimari Mevzuat & Yorumlama Asistanı</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-main: #0B0F19;
            --bg-card: #111827;
            --bg-card-hover: #1F2937;
            --bg-input: #1E293B;
            --border-color: #334155;
            --border-subtle: #1E293B;
            --text-primary: #F8FAFC;
            --text-secondary: #94A3B8;
            --text-muted: #64748B;
            --accent-blue: #38BDF8;
            --accent-indigo: #6366F1;
            --accent-emerald: #10B981;
            --accent-amber: #F59E0B;
            --accent-rose: #F43F5E;
            --radius-sm: 8px;
            --radius-md: 12px;
            --radius-lg: 16px;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background-color: var(--bg-main);
            color: var(--text-primary);
            line-height: 1.5;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        header {
            background: rgba(17, 24, 39, 0.9);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 50;
            padding: 0.85rem 1.5rem;
        }

        .header-container {
            max-width: 1200px;
            margin: 0 auto;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .logo-area { display: flex; align-items: center; gap: 0.75rem; }
        .logo-icon {
            width: 38px; height: 38px;
            background: linear-gradient(135deg, #38BDF8, #6366F1);
            border-radius: var(--radius-sm);
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 1.2rem; color: #fff;
            box-shadow: 0 4px 14px rgba(56, 189, 248, 0.35);
        }

        .logo-title { font-weight: 800; font-size: 1.2rem; letter-spacing: -0.02em; }
        .logo-subtitle { font-size: 0.75rem; color: var(--text-muted); font-weight: 500; }

        .badge-phase {
            background: rgba(56, 189, 248, 0.12);
            color: var(--accent-blue);
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 0.7rem; font-weight: 600; padding: 0.2rem 0.55rem;
            border-radius: 9999px; text-transform: uppercase;
        }

        .nav-tabs { display: flex; gap: 0.5rem; }
        .nav-btn {
            background: transparent; border: 1px solid transparent;
            color: var(--text-secondary); padding: 0.45rem 0.9rem;
            border-radius: var(--radius-sm); font-size: 0.85rem; font-weight: 600;
            cursor: pointer; transition: all 0.2s ease;
        }
        .nav-btn:hover { color: var(--text-primary); background: var(--bg-card-hover); }
        .nav-btn.active { color: #fff; background: var(--bg-input); border-color: var(--border-color); }

        main {
            flex: 1; max-width: 1200px; width: 100%; margin: 0 auto;
            padding: 1.5rem; display: flex; flex-direction: column; gap: 1.5rem;
        }

        .view-section { display: none; }
        .view-section.active { display: block; }

        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: var(--radius-md);
            padding: 1.25rem;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        }

        .select-input, .text-input {
            background: var(--bg-input); border: 1px solid var(--border-color);
            color: var(--text-primary); padding: 0.6rem 0.85rem;
            border-radius: var(--radius-sm); font-size: 0.85rem; outline: none;
        }
        .select-input:focus, .text-input:focus { border-color: var(--accent-blue); }

        .textarea-input {
            width: 100%; min-height: 90px;
            background: var(--bg-input); border: 1px solid var(--border-color);
            color: var(--text-primary); padding: 0.85rem; border-radius: var(--radius-sm);
            font-family: inherit; font-size: 0.95rem; resize: vertical; outline: none;
        }
        .textarea-input:focus { border-color: var(--accent-blue); }

        .btn-submit {
            background: linear-gradient(135deg, #0284C7, #4F46E5);
            color: #fff; border: none; padding: 0.7rem 1.4rem;
            border-radius: var(--radius-sm); font-weight: 700; font-size: 0.9rem;
            cursor: pointer; display: flex; align-items: center; gap: 0.5rem;
            transition: transform 0.1s, opacity 0.2s;
        }
        .btn-submit:hover { opacity: 0.95; transform: translateY(-1px); }

        .quick-questions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.5rem; }
        .quick-label { font-size: 0.75rem; color: var(--text-muted); font-weight: 700; text-transform: uppercase; }
        .quick-btn {
            background: rgba(30, 41, 59, 0.8); border: 1px solid var(--border-subtle);
            color: var(--text-secondary); font-size: 0.75rem; padding: 0.35rem 0.7rem;
            border-radius: 9999px; cursor: pointer; transition: all 0.2s;
        }
        .quick-btn:hover { background: var(--bg-card-hover); color: var(--accent-blue); border-color: var(--accent-blue); }

        /* Interpretation Banner */
        .interp-box {
            background: rgba(15, 23, 42, 0.8);
            border-left: 4px solid var(--accent-indigo);
            border-radius: var(--radius-sm);
            padding: 1.25rem;
            margin-top: 1rem;
            display: flex;
            flex-direction: column;
            gap: 0.85rem;
        }

        .verdict-badge {
            font-size: 0.85rem; font-weight: 800; padding: 0.3rem 0.75rem;
            border-radius: 6px; display: inline-flex; align-items: center; width: fit-content;
        }
        .verdict-uygun { background: rgba(16, 185, 129, 0.2); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.4); }
        .verdict-yetersiz { background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.4); }

        .interp-title { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
        .interp-list { list-style: none; display: flex; flex-direction: column; gap: 0.4rem; font-size: 0.85rem; }
        .interp-list li { display: flex; gap: 0.5rem; }
        .interp-list li::before { content: "•"; color: var(--accent-blue); font-weight: bold; }

        /* Calculation Card */
        .calc-card {
            background: var(--bg-input); border: 1px solid var(--border-color);
            border-radius: var(--radius-sm); padding: 1rem; margin-top: 1rem;
        }
        .calc-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.75rem; margin-top: 0.5rem; }
        .calc-stat { background: rgba(15, 23, 42, 0.5); padding: 0.6rem 0.8rem; border-radius: 6px; border: 1px solid var(--border-subtle); }
        .calc-stat-label { font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600; }
        .calc-stat-val { font-size: 1.1rem; font-weight: 800; color: var(--accent-blue); font-family: 'JetBrains Mono', monospace; }

        .result-body {
            font-size: 0.95rem; color: var(--text-primary); line-height: 1.7;
            white-space: pre-wrap; background: rgba(15, 23, 42, 0.6);
            padding: 1.25rem; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle);
        }

        .citation-item {
            background: var(--bg-input); border-left: 3px solid var(--accent-blue);
            padding: 0.65rem 0.85rem; border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
            margin-bottom: 0.5rem; display: flex; align-items: center; justify-content: space-between; font-size: 0.85rem;
        }
        .citation-badge {
            font-family: 'JetBrains Mono', monospace; background: rgba(56, 189, 248, 0.1);
            color: var(--accent-blue); padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.75rem;
        }

        .evidence-item {
            background: var(--bg-input); border: 1px solid var(--border-subtle);
            border-radius: var(--radius-sm); padding: 0.75rem; font-size: 0.85rem; margin-bottom: 0.5rem;
        }

        .library-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
        .library-table th, .library-table td { padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid var(--border-color); }
        .library-table th { color: var(--text-muted); font-weight: 600; text-transform: uppercase; font-size: 0.75rem; }

        .spinner {
            display: inline-block; width: 16px; height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 50%;
            border-top-color: #fff; animation: spin 0.8s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }

        footer {
            margin-top: auto; border-top: 1px solid var(--border-color);
            padding: 1rem; text-align: center; font-size: 0.75rem; color: var(--text-muted);
        }
    </style>
</head>
<body>

    <header>
        <div class="header-container">
            <div class="logo-area">
                <div class="logo-icon">M</div>
                <div>
                    <div class="logo-title">MİM MEVZUAT</div>
                    <div class="logo-subtitle">Mimari Mevzuat & Yorumlama Asistanı</div>
                </div>
                <span class="badge-phase">NLU + Yorumlama Aktif</span>
            </div>
            <nav class="nav-tabs">
                <button class="nav-btn active" onclick="switchTab('assistant')">💬 Asistan & Doğal Dil</button>
                <button class="nav-btn" onclick="switchTab('calculator')">🧮 Hesap & Yorumlayıcı</button>
                <button class="nav-btn" onclick="switchTab('library')">📚 Mevzuat Kütüphanesi</button>
            </nav>
        </div>
    </header>

    <main>
        <!-- ASSISTANT TAB -->
        <section id="tab-assistant" class="view-section active">
            <div class="card">
                <div style="display: flex; flex-direction: column; gap: 0.85rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <label class="quick-label">Konum / Kapsam:</label>
                        <select id="jurisdiction-select" class="select-input">
                            <option value="TR">🇹🇷 Türkiye Geneli (Otomatik İlçe Tespiti)</option>
                            <option value="TR.Ankara.Cankaya">📍 Ankara / Çankaya</option>
                            <option value="TR.Ankara.Mamak">📍 Ankara / Mamak</option>
                            <option value="TR.Antalya.Finike">📍 Antalya / Finike</option>
                        </select>
                    </div>

                    <textarea id="query-input" class="textarea-input" placeholder="Projenizi veya sorunuzu doğal dille anlatın... Örneğin: 'Çankaya'da 40 dairelik konut projesi yapıyorum, 30 araçlık otopark ayırdım kurtarır mı?' veya '1500 m2 arsam var emsal 1.50, inşaat alanım 2500 m2 oldu aşım var mı?'"></textarea>

                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem;">
                        <div class="quick-questions">
                            <span class="quick-label">Konuşma / Proje Örnekleri:</span>
                            <button class="quick-btn" onclick="setQuery('Çankaya\\'da 40 dairelik konut projesi yapıyorum, 30 araçlık otopark ayırdım kurtarır mı?')">🚗 40 Daire 30 Otopark</button>
                            <button class="quick-btn" onclick="setQuery('1500 m2 arsam var emsal 1.50, toplam inşaat alanım 2500 m2 oldu emsali aşıyor muyum?')">🏢 1500 m² Emsal Aşımı</button>
                            <button class="quick-btn" onclick="setQuery('Bir alanın emsale dahil olup olmadığını nasıl kontrol etmeliyim?')">⚖️ Emsal İstisnaları</button>
                            <button class="quick-btn" onclick="setQuery('Konut binalarında yangın merdiveni ve sığınak hangi şartlarda zorunludur?')">🔥 Yangın & Sığınak</button>
                        </div>
                        <button id="btn-ask" class="btn-submit" onclick="askQuestion()">
                            <span>Sor ve Yorumla</span>
                            <span id="btn-spinner" class="spinner" style="display: none;"></span>
                        </button>
                    </div>
                </div>
            </div>

            <!-- RESULTS CARD -->
            <div id="result-card" class="card" style="display: none; margin-top: 1.5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border-color); padding-bottom: 0.85rem; margin-bottom: 1rem;">
                    <div>
                        <h3 id="res-query-title" style="font-size: 1.1rem; font-weight: 800;"></h3>
                        <span id="res-meta-info" style="font-size: 0.75rem; color: var(--text-muted);"></span>
                    </div>
                    <div style="display: flex; gap: 0.5rem;">
                        <span id="badge-confidence" class="badge-phase"></span>
                        <span id="badge-enforcer" class="badge-phase" style="background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald);">✓ Doğrulandı</span>
                    </div>
                </div>

                <!-- ARCHITECTURAL INTERPRETATION BOX -->
                <div id="interp-box" class="interp-box" style="display: none;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span class="interp-title">🏗️ Uzman Mimari Değerlendirme & Yorumu</span>
                        <span id="interp-verdict" class="verdict-badge"></span>
                    </div>
                    <p id="interp-summary" style="font-size: 0.95rem; line-height: 1.6;"></p>

                    <div id="interp-recs-container">
                        <strong style="font-size: 0.85rem; color: var(--accent-blue); text-transform: uppercase;">📋 Mimari Tasarım & Çözüm Önerileri:</strong>
                        <ul id="interp-recs-list" class="interp-list" style="margin-top: 0.4rem;"></ul>
                    </div>

                    <div id="interp-warnings-container">
                        <strong style="font-size: 0.85rem; color: var(--accent-amber); text-transform: uppercase;">⚠️ Ruhsat & İdare Uyarıları:</strong>
                        <ul id="interp-warnings-list" class="interp-list" style="margin-top: 0.4rem;"></ul>
                    </div>
                </div>

                <!-- CALCULATION STATS BOX -->
                <div id="calc-stats-card" class="calc-card" style="display: none;">
                    <strong style="font-size: 0.85rem; color: var(--text-secondary); text-transform: uppercase;">🧮 Otomatik Hesaplama Çıktıları (Rule Engine):</strong>
                    <div id="calc-stats-grid" class="calc-grid"></div>
                </div>

                <!-- ANSWER TEXT -->
                <div style="margin-top: 1.25rem;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.5rem;">📜 Doğrulanmış Mevzuat Metni</div>
                    <div class="result-body" id="res-answer-body"></div>
                </div>

                <!-- CITATIONS -->
                <div style="margin-top: 1.25rem;">
                    <div style="font-size: 0.85rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; margin-bottom: 0.5rem;">📌 Resmi Atıflar & Dayanaklar</div>
                    <div id="citations-list"></div>
                </div>
            </div>
        </section>

        <!-- CALCULATOR TAB -->
        <section id="tab-calculator" class="view-section">
            <div class="card">
                <h3 style="font-size: 1.1rem; font-weight: 800; margin-bottom: 0.5rem;">🧮 Doğrudan Proje Hesaplayıcı & Mimari Yorumcu</h3>
                <p style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 1.25rem;">Parametreleri girin; sistem kural motorunu çalıştırıp anında mevzuat uygunluk analizi ve mimari çözüm raporu üretsin.</p>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                    <!-- Otopark Formu -->
                    <div style="background: var(--bg-input); padding: 1.25rem; border-radius: var(--radius-sm);">
                        <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--accent-blue); margin-bottom: 0.85rem;">🚗 Konut Otopark Hesabı</h4>
                        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                            <div>
                                <label class="quick-label">Toplam Daire Sayısı:</label>
                                <input id="calc-units" type="number" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="40">
                            </div>
                            <div>
                                <label class="quick-label">Projeye Ayrılan Otopark:</label>
                                <input id="calc-existing-park" type="number" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="30">
                            </div>
                            <button class="btn-submit" style="width: 100%; justify-content: center; margin-top: 0.5rem;" onclick="runDirectParkingCalc()">Otoparkı Hesapla & Yorumla</button>
                        </div>
                    </div>

                    <!-- Emsal Formu -->
                    <div style="background: var(--bg-input); padding: 1.25rem; border-radius: var(--radius-sm);">
                        <h4 style="font-size: 0.95rem; font-weight: 700; color: var(--accent-emerald); margin-bottom: 0.85rem;">🏢 Emsal & TAKS Hesabı</h4>
                        <div style="display: flex; flex-direction: column; gap: 0.75rem;">
                            <div>
                                <label class="quick-label">Parsel Alanı (m²):</label>
                                <input id="calc-parcel" type="number" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="1500">
                            </div>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                                <div>
                                    <label class="quick-label">Emsal (KAKS):</label>
                                    <input id="calc-kaks" type="number" step="0.1" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="1.5">
                                </div>
                                <div>
                                    <label class="quick-label">TAKS:</label>
                                    <input id="calc-taks" type="number" step="0.05" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="0.35">
                                </div>
                            </div>
                            <div>
                                <label class="quick-label">Önerilen Emsal Alanı (m²):</label>
                                <input id="calc-proposed-area" type="number" class="text-input" style="width: 100%; margin-top: 0.25rem;" value="2400">
                            </div>
                            <button class="btn-submit" style="width: 100%; justify-content: center; margin-top: 0.5rem;" onclick="runDirectEmsalCalc()">Emsali Hesapla & Yorumla</button>
                        </div>
                    </div>
                </div>

                <!-- Direct Calc Result -->
                <div id="direct-calc-res" class="interp-box" style="display: none; margin-top: 1.5rem;">
                    <div style="display: flex; align-items: center; justify-content: space-between;">
                        <span class="interp-title" id="dcalc-title"></span>
                        <span id="dcalc-verdict" class="verdict-badge"></span>
                    </div>
                    <p id="dcalc-summary" style="font-size: 0.95rem; line-height: 1.6;"></p>
                    <div id="dcalc-recs-container">
                        <strong style="font-size: 0.85rem; color: var(--accent-blue); text-transform: uppercase;">📋 Mimari Öneriler:</strong>
                        <ul id="dcalc-recs-list" class="interp-list" style="margin-top: 0.4rem;"></ul>
                    </div>
                </div>
            </div>
        </section>

        <!-- LIBRARY TAB -->
        <section id="tab-library" class="view-section">
            <div class="card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <div>
                        <h3 style="font-size: 1.1rem; font-weight: 800;">Yüklü Resmi Mevzuat Belgeleri</h3>
                        <p style="font-size: 0.8rem; color: var(--text-muted);">mevzuat.gov.tr konsolide metinlerinden ayrıştırılmış aktif mevzuat kümesi</p>
                    </div>
                    <button class="nav-btn" onclick="loadDocuments()">🔄 Yenile</button>
                </div>

                <table class="library-table">
                    <thead>
                        <tr>
                            <th>Yönetmelik Adı</th>
                            <th>Yetkili Kurum</th>
                            <th>Kapsam</th>
                            <th>Versiyon</th>
                            <th>Madde Sayısı</th>
                            <th>Resmi Link</th>
                        </tr>
                    </thead>
                    <tbody id="library-table-body">
                        <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Yükleniyor...</td></tr>
                    </tbody>
                </table>
            </div>
        </section>
    </main>

    <footer>
        <div style="max-width: 1000px; margin: 0 auto; line-height: 1.6;">
            <strong>MİM MEVZUAT © 2026</strong> — Türkiye Doğrulanmış Mimari Mevzuat & Yorumlama Asistanı<br>
            <span style="color: var(--text-secondary); font-size: 0.72rem;">
                ⚠️ <em>Yasal Uyarı: Bu asistan bir mimari karar destek ve ön etüt aracıdır. Nihai yapı ruhsatı ve imar durumu süreçlerinde ilgili belediye ve resmi idarelerin onaylı meri mevzuat kararları esastır.</em>
            </span>
        </div>
    </footer>

    <script>
        function switchTab(tabId) {
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));

            document.getElementById('tab-' + tabId).classList.add('active');
            event.currentTarget.classList.add('active');

            if (tabId === 'library') loadDocuments();
        }

        function setQuery(text) {
            document.getElementById('query-input').value = text;
        }

        async function askQuestion() {
            const queryInput = document.getElementById('query-input');
            const jurisdictionSelect = document.getElementById('jurisdiction-select');
            const query = queryInput.value.trim();
            if (!query) return;

            const btnAsk = document.getElementById('btn-ask');
            const spinner = document.getElementById('btn-spinner');
            const resultCard = document.getElementById('result-card');

            btnAsk.disabled = true;
            spinner.style.display = 'inline-block';

            try {
                const response = await fetch('/api/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        query: query,
                        jurisdiction: jurisdictionSelect.value === 'TR' ? null : jurisdictionSelect.value,
                        limit: 5
                    })
                });

                if (!response.ok) throw new Error('Sorgu işlenirken bir hata oluştu.');
                const data = await response.json();
                renderResult(data);
            } catch (err) {
                alert('Hata: ' + err.message);
            } finally {
                btnAsk.disabled = false;
                spinner.style.display = 'none';
            }
        }

        function renderResult(data) {
            const card = document.getElementById('result-card');
            card.style.display = 'block';

            document.getElementById('res-query-title').innerText = data.query;
            document.getElementById('res-meta-info').innerText =
                `Süre: ${data.duration_ms} ms | Kapsam: ${data.jurisdiction} | Niyet: ${data.intent.type}`;

            document.getElementById('badge-confidence').innerText = 'Güven: ' + data.answer.confidence;

            // INTERPRETATION
            const interpBox = document.getElementById('interp-box');
            if (data.interpretation) {
                interpBox.style.display = 'flex';
                const vBadge = document.getElementById('interp-verdict');
                vBadge.innerText = data.interpretation.verdict;
                vBadge.className = 'verdict-badge ' + (data.interpretation.verdict.includes('UYGUN') ? 'verdict-uygun' : 'verdict-yetersiz');
                document.getElementById('interp-summary').innerText = data.interpretation.summary;

                const recsList = document.getElementById('interp-recs-list');
                recsList.innerHTML = '';
                data.interpretation.design_recommendations.forEach(r => {
                    const li = document.createElement('li');
                    li.innerText = r;
                    recsList.appendChild(li);
                });

                const warnList = document.getElementById('interp-warnings-list');
                warnList.innerHTML = '';
                data.interpretation.authority_warnings.forEach(w => {
                    const li = document.createElement('li');
                    li.innerText = w;
                    warnList.appendChild(li);
                });
            } else {
                interpBox.style.display = 'none';
            }

            // CALCULATION STATS
            const calcBox = document.getElementById('calc-stats-card');
            const calcGrid = document.getElementById('calc-stats-grid');
            if (data.calculation_traces && data.calculation_traces.length > 0) {
                calcBox.style.display = 'block';
                calcGrid.innerHTML = '';
                data.calculation_traces.forEach(ct => {
                    for (const [key, val] of Object.entries(ct.result)) {
                        const stat = document.createElement('div');
                        stat.className = 'calc-stat';
                        stat.innerHTML = `
                            <div class="calc-stat-label">${key.replace(/_/g, ' ')}</div>
                            <div class="calc-stat-val">${val}</div>
                        `;
                        calcGrid.appendChild(stat);
                    }
                });
            } else {
                calcBox.style.display = 'none';
            }

            // BODY & CITATIONS
            document.getElementById('res-answer-body').innerText = data.answer.body;

            const citContainer = document.getElementById('citations-list');
            citContainer.innerHTML = '';
            if (data.answer.citations) {
                data.answer.citations.forEach(c => {
                    const div = document.createElement('div');
                    div.className = 'citation-item';
                    const pText = c.paragraph ? ` Fıkra ${c.paragraph}` : '';
                    div.innerHTML = `
                        <div>
                            <span class="citation-badge">${c.article}${pText}</span>
                            <span>${c.document_id}</span>
                        </div>
                        <a href="${c.source_url}" target="_blank" style="color: var(--accent-blue); text-decoration: none; font-size: 0.75rem;">Resmi Mevzuat Linki ↗</a>
                    `;
                    citContainer.appendChild(div);
                });
            }

            card.scrollIntoView({ behavior: 'smooth' });
        }

        async function runDirectParkingCalc() {
            const units = parseInt(document.getElementById('calc-units').value);
            const existing = parseInt(document.getElementById('calc-existing-park').value);

            try {
                const res = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rule_id: 'rule:otopark:konut:v2022',
                        inputs: { unit_count: units, existing_parking: existing },
                        project_name: 'Konut Otopark Denetimi'
                    })
                });
                const data = await res.json();
                renderDirectCalcResult('Otopark Uygunluk Raporu', data);
            } catch (err) {
                alert('Hesaplama hatası: ' + err.message);
            }
        }

        async function runDirectEmsalCalc() {
            const parcel = parseFloat(document.getElementById('calc-parcel').value);
            const kaks = parseFloat(document.getElementById('calc-kaks').value);
            const taks = parseFloat(document.getElementById('calc-taks').value);
            const proposed = parseFloat(document.getElementById('calc-proposed-area').value);

            try {
                const res = await fetch('/api/calculate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        rule_id: 'rule:imar:emsal_taks:v2026',
                        inputs: { parcel_area: parcel, kaks: kaks, taks: taks, actual_emsal_area: proposed },
                        project_name: 'Emsal/TAKS Denetimi'
                    })
                });
                const data = await res.json();
                renderDirectCalcResult('Emsal ve TAKS Uygunluk Raporu', data);
            } catch (err) {
                alert('Hesaplama hatası: ' + err.message);
            }
        }

        function renderDirectCalcResult(title, data) {
            const box = document.getElementById('direct-calc-res');
            box.style.display = 'flex';
            document.getElementById('dcalc-title').innerText = title;

            const vBadge = document.getElementById('dcalc-verdict');
            vBadge.innerText = data.interpretation.verdict;
            vBadge.className = 'verdict-badge ' + (data.interpretation.verdict.includes('UYGUN') ? 'verdict-uygun' : 'verdict-yetersiz');

            document.getElementById('dcalc-summary').innerText = data.interpretation.summary;

            const recsList = document.getElementById('dcalc-recs-list');
            recsList.innerHTML = '';
            data.interpretation.design_recommendations.forEach(r => {
                const li = document.createElement('li');
                li.innerText = r;
                recsList.appendChild(li);
            });
            box.scrollIntoView({ behavior: 'smooth' });
        }

        async function loadDocuments() {
            const tbody = document.getElementById('library-table-body');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Yükleniyor...</td></tr>';
            try {
                const res = await fetch('/api/documents');
                const data = await res.json();
                tbody.innerHTML = '';
                data.documents.forEach(doc => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${doc.title}</strong></td>
                        <td>${doc.authority}</td>
                        <td><span class="citation-badge">${doc.jurisdiction}</span></td>
                        <td>${doc.version}</td>
                        <td>${doc.article_count}</td>
                        <td><a href="${doc.source_url}" target="_blank" style="color: var(--accent-blue);">mevzuat.gov.tr ↗</a></td>
                    `;
                    tbody.appendChild(tr);
                });
            } catch (err) {
                tbody.innerHTML = `<tr><td colspan="6" style="color: var(--accent-rose);">Hata: ${err.message}</td></tr>`;
            }
        }
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def index():
    """Web arayüzü ana sayfası."""
    return HTMLResponse(content=INDEX_HTML)


def run_server(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
