CREATE TABLE IF NOT EXISTS audit_events (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 module TEXT NOT NULL,
 entity TEXT NOT NULL,
 entity_id INTEGER,
 actor TEXT NOT NULL,
 action TEXT NOT NULL,
 from_status TEXT,
 to_status TEXT,
 notes TEXT NOT NULL DEFAULT '',
 occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(occurred_at);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_events(module, entity, entity_id);
