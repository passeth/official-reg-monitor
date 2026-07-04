CREATE TABLE IF NOT EXISTS sources (
  source_id TEXT PRIMARY KEY,
  jurisdiction TEXT NOT NULL,
  name TEXT NOT NULL,
  official_owner TEXT,
  url TEXT NOT NULL,
  kind TEXT,
  cadence TEXT,
  parser TEXT,
  registry_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS source_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id TEXT NOT NULL,
  fetched_at TEXT NOT NULL,
  url TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  etag TEXT,
  last_modified TEXT,
  sha256 TEXT,
  byte_size INTEGER,
  path TEXT,
  changed INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE INDEX IF NOT EXISTS idx_source_snapshots_source_time
ON source_snapshots(source_id, fetched_at);

CREATE INDEX IF NOT EXISTS idx_source_snapshots_hash
ON source_snapshots(source_id, sha256);

CREATE TABLE IF NOT EXISTS snapshot_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_snapshot_id INTEGER NOT NULL,
  url TEXT NOT NULL,
  http_status INTEGER,
  content_type TEXT,
  sha256 TEXT,
  byte_size INTEGER,
  path TEXT,
  error TEXT,
  FOREIGN KEY (source_snapshot_id) REFERENCES source_snapshots(id)
);

CREATE INDEX IF NOT EXISTS idx_snapshot_assets_snapshot
ON snapshot_assets(source_snapshot_id);

CREATE TABLE IF NOT EXISTS regulatory_sources (
  source_code TEXT PRIMARY KEY,
  source_id TEXT NOT NULL,
  jurisdiction TEXT NOT NULL,
  official_owner TEXT,
  official_url TEXT NOT NULL,
  parser TEXT,
  notes TEXT,
  FOREIGN KEY (source_id) REFERENCES sources(source_id)
);

CREATE TABLE IF NOT EXISTS source_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_code TEXT NOT NULL,
  source_snapshot_id INTEGER NOT NULL,
  version_label TEXT,
  effective_date TEXT,
  published_date TEXT,
  parsed_at TEXT NOT NULL,
  parser_version TEXT,
  FOREIGN KEY (source_code) REFERENCES regulatory_sources(source_code),
  FOREIGN KEY (source_snapshot_id) REFERENCES source_snapshots(id)
);

CREATE TABLE IF NOT EXISTS ingredients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  canonical_inci_name TEXT NOT NULL,
  korean_name TEXT,
  cas_number TEXT,
  ec_number TEXT,
  normalized_key TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ingredients_normalized_key
ON ingredients(normalized_key);

CREATE TABLE IF NOT EXISTS ingredient_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ingredient_id INTEGER NOT NULL,
  alias_name TEXT NOT NULL,
  alias_type TEXT NOT NULL,
  normalized_key TEXT NOT NULL,
  source_version_id INTEGER,
  FOREIGN KEY (ingredient_id) REFERENCES ingredients(id),
  FOREIGN KEY (source_version_id) REFERENCES source_versions(id)
);

CREATE INDEX IF NOT EXISTS idx_ingredient_aliases_key
ON ingredient_aliases(normalized_key);

CREATE TABLE IF NOT EXISTS regulatory_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_version_id INTEGER NOT NULL,
  jurisdiction TEXT NOT NULL,
  source_code TEXT NOT NULL,
  annex_or_part TEXT,
  reference_no TEXT,
  ingredient_id INTEGER,
  ingredient_name_raw TEXT NOT NULL,
  cas_number_raw TEXT,
  ec_number_raw TEXT,
  status TEXT NOT NULL,
  max_percent REAL,
  max_concentration_raw TEXT,
  product_scope TEXT,
  body_part_scope TEXT,
  warning_label TEXT,
  conditions_raw TEXT,
  note_raw TEXT,
  official_row_hash TEXT NOT NULL,
  FOREIGN KEY (source_version_id) REFERENCES source_versions(id),
  FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)
);

CREATE INDEX IF NOT EXISTS idx_regulatory_items_jurisdiction_status
ON regulatory_items(jurisdiction, status);

CREATE INDEX IF NOT EXISTS idx_regulatory_items_ingredient
ON regulatory_items(ingredient_id);

CREATE TABLE IF NOT EXISTS regulatory_item_conditions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  regulatory_item_id INTEGER NOT NULL,
  condition_type TEXT NOT NULL,
  condition_value TEXT,
  max_percent REAL,
  note TEXT,
  FOREIGN KEY (regulatory_item_id) REFERENCES regulatory_items(id)
);

CREATE TABLE IF NOT EXISTS parser_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_snapshot_id INTEGER NOT NULL,
  parser TEXT NOT NULL,
  parser_version TEXT,
  started_at TEXT NOT NULL,
  finished_at TEXT,
  status TEXT NOT NULL,
  records_parsed INTEGER DEFAULT 0,
  records_inserted INTEGER DEFAULT 0,
  warnings TEXT,
  error TEXT,
  FOREIGN KEY (source_snapshot_id) REFERENCES source_snapshots(id)
);
