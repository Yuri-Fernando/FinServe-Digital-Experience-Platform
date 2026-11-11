CREATE TABLE IF NOT EXISTS content_items (
 id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE,
 component TEXT NOT NULL CHECK(component IN ('campaignhero','promobanner','ratecard')),
 eyebrow TEXT NOT NULL, title TEXT NOT NULL, body TEXT NOT NULL,
 cta_label TEXT NOT NULL, cta_url TEXT NOT NULL,
 segment TEXT NOT NULL CHECK(segment IN ('all','investidor','credito','jovem')),
 status TEXT NOT NULL CHECK(status IN ('DRAFT','IN_REVIEW','APPROVED','PUBLISHED','ARCHIVED')),
 version INTEGER NOT NULL DEFAULT 1, owner TEXT NOT NULL,
 updated_at TEXT NOT NULL, published_at TEXT
);
CREATE TABLE IF NOT EXISTS content_revisions (
 id INTEGER PRIMARY KEY AUTOINCREMENT, content_id INTEGER NOT NULL REFERENCES content_items(id),
 version INTEGER NOT NULL, snapshot TEXT NOT NULL, actor TEXT NOT NULL, reason TEXT NOT NULL, created_at TEXT NOT NULL,
 UNIQUE(content_id, version)
);
CREATE INDEX IF NOT EXISTS idx_content_status_segment ON content_items(status,segment);
