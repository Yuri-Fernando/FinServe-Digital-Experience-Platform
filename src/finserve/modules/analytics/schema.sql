CREATE TABLE IF NOT EXISTS campaigns (
 id INTEGER PRIMARY KEY, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 channel TEXT NOT NULL CHECK(channel IN ('Paid Search','Social','Email','Organic')),
 product TEXT NOT NULL, audience TEXT NOT NULL,
 monthly_budget_brl REAL NOT NULL CHECK(monthly_budget_brl>=0),
 state TEXT NOT NULL CHECK(state IN ('active','paused','planned'))
);
CREATE TABLE IF NOT EXISTS dim_date (
 date_key INTEGER PRIMARY KEY, day TEXT UNIQUE NOT NULL, week_day INTEGER NOT NULL, month INTEGER NOT NULL, year INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS fact_experience_daily (
 id INTEGER PRIMARY KEY AUTOINCREMENT, date_key INTEGER NOT NULL REFERENCES dim_date(date_key),
 campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
 impressions INTEGER NOT NULL CHECK(impressions>=0), clicks INTEGER NOT NULL CHECK(clicks>=0),
 leads INTEGER NOT NULL CHECK(leads>=0), approvals INTEGER NOT NULL CHECK(approvals>=0),
 sessions INTEGER NOT NULL CHECK(sessions>=0), spend_brl REAL NOT NULL CHECK(spend_brl>=0),
 attributable_revenue_brl REAL NOT NULL CHECK(attributable_revenue_brl>=0),
 lcp_ms INTEGER NOT NULL, inp_ms INTEGER NOT NULL, cls_milli INTEGER NOT NULL,
 UNIQUE(date_key,campaign_id), CHECK(clicks<=impressions), CHECK(leads<=clicks), CHECK(approvals<=leads)
);
CREATE TABLE IF NOT EXISTS ab_tests (
 id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 campaign_id INTEGER NOT NULL REFERENCES campaigns(id), metric TEXT NOT NULL, hypothesis TEXT NOT NULL,
 started_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ab_variants (
 test_id INTEGER NOT NULL REFERENCES ab_tests(id), variant TEXT NOT NULL,
 visitors INTEGER NOT NULL CHECK(visitors>0), conversions INTEGER NOT NULL CHECK(conversions>=0),
 PRIMARY KEY(test_id, variant), CHECK(conversions<=visitors)
);
CREATE INDEX IF NOT EXISTS idx_fact_date ON fact_experience_daily(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_campaign_date ON fact_experience_daily(campaign_id,date_key);
CREATE VIEW IF NOT EXISTS vw_daily_performance AS
 SELECT d.day, c.name AS campaign, c.channel, c.audience, c.product,
 f.impressions,f.clicks,f.leads,f.approvals,f.sessions,f.spend_brl,f.attributable_revenue_brl,
 f.lcp_ms,f.inp_ms,f.cls_milli
 FROM fact_experience_daily f JOIN dim_date d ON d.date_key=f.date_key JOIN campaigns c ON c.id=f.campaign_id;
