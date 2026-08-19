-- MİM MEVZUAT - SQLite şema
-- DATA_MODEL.txt bölüm 1-2, 4-7 ile birebir uyumlu.
-- İlke: bir Document/Article yerinde değiştirilmez (bkz. DATA_MODEL.txt
-- bölüm 8) - değişiklik = yeni satır + supersedes/superseded_by zinciri.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS document (
    document_id           TEXT PRIMARY KEY,
    title                 TEXT NOT NULL,
    authority              TEXT,
    document_type          TEXT NOT NULL,
    jurisdiction            TEXT NOT NULL,
    publication_date         TEXT,
    effective_date            TEXT,
    last_amended_date          TEXT,
    version                     TEXT NOT NULL,
    source_url                   TEXT NOT NULL,
    official_source_tier           INTEGER NOT NULL CHECK (official_source_tier BETWEEN 1 AND 7),
    retrieved_at                     TEXT NOT NULL,
    validity_status                   TEXT NOT NULL CHECK (
        validity_status IN ('ACTIVE', 'SUPERSEDED', 'REPEALED', 'PENDING_REVIEW')
    ),
    supersedes             TEXT REFERENCES document (document_id),
    superseded_by           TEXT REFERENCES document (document_id),
    topics                    TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS article (
    article_id      TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES document (document_id),
    article         TEXT NOT NULL,
    paragraph       TEXT,
    subparagraph    TEXT,
    text            TEXT NOT NULL,
    effective_from  TEXT,
    effective_to    TEXT,
    jurisdiction    TEXT NOT NULL,
    topics          TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_article_document ON article (document_id);
CREATE INDEX IF NOT EXISTS idx_article_jurisdiction ON article (jurisdiction);

-- BM25 tam metin arama - RAG_DESIGN.txt bolum 1. Bagimsiz bir FTS5
-- tablosu (content= linkage kullanilmadi cunku article_id TEXT PK'dir,
-- rowid tabanli linkage gereksiz karmasiklik katardi); article ile
-- senkron trigger'larla tutulur.
CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5 (
    article_id UNINDEXED,
    document_id UNINDEXED,
    text
);

CREATE TRIGGER IF NOT EXISTS article_fts_ai AFTER INSERT ON article BEGIN
    INSERT INTO article_fts (article_id, document_id, text)
    VALUES (new.article_id, new.document_id, new.text);
END;

CREATE TRIGGER IF NOT EXISTS article_fts_ad AFTER DELETE ON article BEGIN
    DELETE FROM article_fts WHERE article_id = old.article_id;
END;

CREATE TRIGGER IF NOT EXISTS article_fts_au AFTER UPDATE ON article BEGIN
    DELETE FROM article_fts WHERE article_id = old.article_id;
    INSERT INTO article_fts (article_id, document_id, text)
    VALUES (new.article_id, new.document_id, new.text);
END;

-- Project Mode - DATA_MODEL.txt bolum 4
CREATE TABLE IF NOT EXISTS project (
    project_id                 TEXT PRIMARY KEY,
    project_name                TEXT NOT NULL,
    province                     TEXT,
    district                      TEXT,
    parcel_area                    REAL,
    kaks                             REAL,
    taks                              REAL,
    building_type                      TEXT,
    unit_count                          INTEGER,
    commercial_area                       REAL,
    residential_area                        REAL,
    parking_count                             INTEGER,
    accessible_parking_count                    INTEGER,
    ev_parking_count                              INTEGER,
    storey_count                                    INTEGER,
    basement_count                                    INTEGER,
    created_at                                          TEXT NOT NULL,
    updated_at                                            TEXT NOT NULL
);

-- Rule Engine - RULE_ENGINE.txt bolum 2. "formula_ref" alani
-- calistirilabilir kod DEGIL, kayitli/test edilmis bir Python
-- fonksiyonunun ADI'dir (SECURITY.txt bolum 5: eval() tarzi dinamik
-- kod uretimi YASAK).
CREATE TABLE IF NOT EXISTS rule_pack (
    rule_id           TEXT PRIMARY KEY,
    jurisdiction      TEXT NOT NULL,
    version           TEXT NOT NULL,
    source_document   TEXT NOT NULL REFERENCES document (document_id),
    source_article    TEXT NOT NULL,
    inputs_json       TEXT NOT NULL,
    formula_ref       TEXT NOT NULL,
    conditions        TEXT,
    exceptions        TEXT,
    effective_from    TEXT,
    effective_to      TEXT
);

CREATE TABLE IF NOT EXISTS calculation_trace (
    trace_id          TEXT PRIMARY KEY,
    rule_id           TEXT NOT NULL REFERENCES rule_pack (rule_id),
    inputs_json       TEXT NOT NULL,
    method            TEXT NOT NULL,
    result_json       TEXT NOT NULL,
    source_document   TEXT NOT NULL,
    source_article    TEXT NOT NULL,
    confidence        TEXT NOT NULL,
    generated_at      TEXT NOT NULL
);

-- Answer - DATA_MODEL.txt bolum 7. source_versions_json DONUK bir
-- kopyadir: sonradan mevzuat degisse bile bu kayit degismez.
CREATE TABLE IF NOT EXISTS answer (
    answer_id                  TEXT PRIMARY KEY,
    query_text                 TEXT NOT NULL,
    resolved_context            TEXT,
    retrieved_article_ids_json   TEXT NOT NULL,
    source_versions_json          TEXT NOT NULL,
    confidence_level                TEXT NOT NULL CHECK (
        confidence_level IN ('HIGH', 'MEDIUM', 'LOW', 'NEEDS_AUTHORITY_REVIEW')
    ),
    calculation_trace_id   TEXT REFERENCES calculation_trace (trace_id),
    created_at              TEXT NOT NULL
);
