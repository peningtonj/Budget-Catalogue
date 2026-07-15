PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS source_document (
    id INTEGER PRIMARY KEY,
    budget_year TEXT NOT NULL,
    paper_code TEXT,
    title TEXT,
    file_path TEXT,
    sha256 TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS measure (
    id INTEGER PRIMARY KEY,
    source_document_id INTEGER NOT NULL,
    portfolio_name TEXT NOT NULL,
    measure_title TEXT NOT NULL,
    document_section TEXT NOT NULL CHECK (document_section IN ('payment', 'receipt')),
    source_page INTEGER,
    full_measure_text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_document_id, measure_title, source_page),
    FOREIGN KEY (source_document_id) REFERENCES source_document(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS measure_headline_financial (
    id INTEGER PRIMARY KEY,
    measure_id INTEGER NOT NULL,
    impact_type TEXT NOT NULL CHECK (impact_type IN ('Payment', 'Receipt')),
    department_name TEXT NOT NULL,
    is_related INTEGER NOT NULL DEFAULT 0 CHECK (is_related IN (0, 1)),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
    UNIQUE (measure_id, impact_type, department_name, is_related),
    FOREIGN KEY (measure_id) REFERENCES measure(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS measure_headline_financial_value (
    id INTEGER PRIMARY KEY,
    headline_financial_id INTEGER NOT NULL,
    fiscal_year TEXT NOT NULL,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('numeric', 'nfp', 'blank', 'other')),
    value_numeric_million NUMERIC,
    value_raw TEXT,
    UNIQUE (headline_financial_id, fiscal_year),
    FOREIGN KEY (headline_financial_id) REFERENCES measure_headline_financial(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS measure_component (
    id INTEGER PRIMARY KEY,
    measure_id INTEGER NOT NULL,
    parent_component_id INTEGER,
    level INTEGER NOT NULL CHECK (level IN (1, 2)),
    marker TEXT NOT NULL CHECK (marker IN ('dot', 'dash')),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
    component_text TEXT NOT NULL,
    amount_raw TEXT,
    amount_million NUMERIC,
    start_fiscal_year TEXT,
    duration_years INTEGER,
    allocation_status TEXT NOT NULL DEFAULT 'unknown' CHECK (allocation_status IN ('allocated', 'unallocated', 'unknown')),
    FOREIGN KEY (measure_id) REFERENCES measure(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_component_id) REFERENCES measure_component(id) ON DELETE CASCADE,
    CHECK (NOT (level = 1 AND parent_component_id IS NOT NULL)),
    CHECK (NOT (level = 2 AND parent_component_id IS NULL)),
    CHECK (NOT (level = 1 AND marker != 'dot')),
    CHECK (NOT (level = 2 AND marker != 'dash'))
);

CREATE TABLE IF NOT EXISTS measure_component_impact (
    id INTEGER PRIMARY KEY,
    component_id INTEGER NOT NULL,
    impact_type TEXT NOT NULL CHECK (impact_type IN ('Payment', 'Receipt')),
    fiscal_year TEXT NOT NULL,
    value_kind TEXT NOT NULL CHECK (value_kind IN ('numeric', 'nfp', 'blank', 'other')),
    value_numeric_million NUMERIC,
    value_raw TEXT,
    UNIQUE (component_id, impact_type, fiscal_year),
    FOREIGN KEY (component_id) REFERENCES measure_component(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS measure_related_measure (
    id INTEGER PRIMARY KEY,
    measure_id INTEGER NOT NULL,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 1),
    related_measure_title TEXT NOT NULL,
    UNIQUE (measure_id, related_measure_title),
    FOREIGN KEY (measure_id) REFERENCES measure(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_measure_source_document_id ON measure(source_document_id);
CREATE INDEX IF NOT EXISTS idx_measure_title ON measure(measure_title);
CREATE INDEX IF NOT EXISTS idx_measure_portfolio ON measure(portfolio_name);
CREATE INDEX IF NOT EXISTS idx_measure_document_section ON measure(document_section);
CREATE INDEX IF NOT EXISTS idx_headline_measure_id ON measure_headline_financial(measure_id);
CREATE INDEX IF NOT EXISTS idx_headline_department ON measure_headline_financial(department_name);
CREATE INDEX IF NOT EXISTS idx_headline_value_year ON measure_headline_financial_value(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_component_measure_id ON measure_component(measure_id);
CREATE INDEX IF NOT EXISTS idx_component_parent_id ON measure_component(parent_component_id);
CREATE INDEX IF NOT EXISTS idx_component_level_marker ON measure_component(level, marker);
CREATE INDEX IF NOT EXISTS idx_component_impact_component_id ON measure_component_impact(component_id);
CREATE INDEX IF NOT EXISTS idx_related_measure_measure_id ON measure_related_measure(measure_id);
