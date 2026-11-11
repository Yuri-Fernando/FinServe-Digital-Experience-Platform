CREATE TABLE IF NOT EXISTS market_series (
 id TEXT PRIMARY KEY,
 sgs_code INTEGER NOT NULL,
 name TEXT NOT NULL,
 unit TEXT NOT NULL,
 frequency TEXT NOT NULL CHECK(frequency IN ('daily','monthly')),
 description TEXT NOT NULL,
 source_url TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS market_observations (
 series_id TEXT NOT NULL REFERENCES market_series(id),
 obs_date TEXT NOT NULL,
 value REAL NOT NULL,
 PRIMARY KEY (series_id, obs_date)
);
CREATE TABLE IF NOT EXISTS market_expectations (
 indicator TEXT NOT NULL,
 reference_year TEXT NOT NULL,
 obs_date TEXT NOT NULL,
 median REAL, mean REAL, std REAL, min REAL, max REAL, respondents INTEGER,
 PRIMARY KEY (indicator, reference_year, obs_date)
);
CREATE TABLE IF NOT EXISTS market_sync_log (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 at TEXT NOT NULL,
 source TEXT NOT NULL,
 series_id TEXT,
 rows INTEGER NOT NULL DEFAULT 0,
 status TEXT NOT NULL CHECK(status IN ('ok','error')),
 detail TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_market_obs_date ON market_observations(series_id, obs_date);
