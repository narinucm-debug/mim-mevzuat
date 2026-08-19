-- MİM MEVZUAT - FTS5 tam metin arama eklentisi
-- schema.sql'den AYRI tutulur çünkü bazı SQLite derlemelerinde FTS5
-- modülü bulunmayabilir (ör. Android/Chaquopy'nin gömdüğü SQLite -
-- 2026-08-19'da bir tablette "no such module: fts5" hatasıyla
-- doğrulandı). db.py bu dosyayı best-effort uygular: başarısız olursa
-- sistem çökmez, RetrievalEngine otomatik olarak FTS5'siz (basit
-- filtre + Python taraflı terim eşleştirme) moda geçer - bkz.
-- retrieval.py.

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
