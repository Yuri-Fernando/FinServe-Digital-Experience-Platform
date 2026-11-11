# Dicionário de dados

Gerado por `python -m finserve dictionary` a partir do schema real (PRAGMA table_info). Não editar à mão.

## `audit_events` — módulo `platform`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `module` | TEXT | sim |  |
| `entity` | TEXT | sim |  |
| `entity_id` | INTEGER | não |  |
| `actor` | TEXT | sim |  |
| `action` | TEXT | sim |  |
| `from_status` | TEXT | não |  |
| `to_status` | TEXT | não |  |
| `notes` | TEXT | sim |  |
| `occurred_at` | TEXT | sim |  |

## `content_items` — módulo `experience`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `key` | TEXT | sim |  |
| `component` | TEXT | sim |  |
| `eyebrow` | TEXT | sim |  |
| `title` | TEXT | sim |  |
| `body` | TEXT | sim |  |
| `cta_label` | TEXT | sim |  |
| `cta_url` | TEXT | sim |  |
| `segment` | TEXT | sim |  |
| `status` | TEXT | sim |  |
| `version` | INTEGER | sim |  |
| `owner` | TEXT | sim |  |
| `updated_at` | TEXT | sim |  |
| `published_at` | TEXT | não |  |

## `content_revisions` — módulo `experience`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `content_id` | INTEGER | sim |  |
| `version` | INTEGER | sim |  |
| `snapshot` | TEXT | sim |  |
| `actor` | TEXT | sim |  |
| `reason` | TEXT | sim |  |
| `created_at` | TEXT | sim |  |

## `campaigns` — módulo `analytics`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `slug` | TEXT | sim |  |
| `name` | TEXT | sim |  |
| `channel` | TEXT | sim |  |
| `product` | TEXT | sim |  |
| `audience` | TEXT | sim |  |
| `monthly_budget_brl` | REAL | sim |  |
| `state` | TEXT | sim |  |

## `dim_date` — módulo `analytics`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `date_key` | INTEGER | não | sim |
| `day` | TEXT | sim |  |
| `week_day` | INTEGER | sim |  |
| `month` | INTEGER | sim |  |
| `year` | INTEGER | sim |  |

## `fact_experience_daily` — módulo `analytics`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `date_key` | INTEGER | sim |  |
| `campaign_id` | INTEGER | sim |  |
| `impressions` | INTEGER | sim |  |
| `clicks` | INTEGER | sim |  |
| `leads` | INTEGER | sim |  |
| `approvals` | INTEGER | sim |  |
| `sessions` | INTEGER | sim |  |
| `spend_brl` | REAL | sim |  |
| `attributable_revenue_brl` | REAL | sim |  |
| `lcp_ms` | INTEGER | sim |  |
| `inp_ms` | INTEGER | sim |  |
| `cls_milli` | INTEGER | sim |  |

## `ab_tests` — módulo `analytics`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `key` | TEXT | sim |  |
| `name` | TEXT | sim |  |
| `campaign_id` | INTEGER | sim |  |
| `metric` | TEXT | sim |  |
| `hypothesis` | TEXT | sim |  |
| `started_at` | TEXT | sim |  |

## `ab_variants` — módulo `analytics`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `test_id` | INTEGER | sim | sim |
| `variant` | TEXT | sim | sim |
| `visitors` | INTEGER | sim |  |
| `conversions` | INTEGER | sim |  |

## `market_series` — módulo `market`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | TEXT | não | sim |
| `sgs_code` | INTEGER | sim |  |
| `name` | TEXT | sim |  |
| `unit` | TEXT | sim |  |
| `frequency` | TEXT | sim |  |
| `description` | TEXT | sim |  |
| `source_url` | TEXT | sim |  |

## `market_observations` — módulo `market`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `series_id` | TEXT | sim | sim |
| `obs_date` | TEXT | sim | sim |
| `value` | REAL | sim |  |

## `market_expectations` — módulo `market`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `indicator` | TEXT | sim | sim |
| `reference_year` | TEXT | sim | sim |
| `obs_date` | TEXT | sim | sim |
| `median` | REAL | não |  |
| `mean` | REAL | não |  |
| `std` | REAL | não |  |
| `min` | REAL | não |  |
| `max` | REAL | não |  |
| `respondents` | INTEGER | não |  |

## `market_sync_log` — módulo `market`

| Coluna | Tipo | Obrigatória | PK |
|---|---|---|---|
| `id` | INTEGER | não | sim |
| `at` | TEXT | sim |  |
| `source` | TEXT | sim |  |
| `series_id` | TEXT | não |  |
| `rows` | INTEGER | sim |  |
| `status` | TEXT | sim |  |
| `detail` | TEXT | sim |  |

