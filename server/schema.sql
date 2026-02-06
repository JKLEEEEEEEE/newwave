-- scoring_modules table
CREATE TABLE IF NOT EXISTS scoring_modules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_key TEXT UNIQUE NOT NULL,
    module_name TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0
);

-- scoring_items table
CREATE TABLE IF NOT EXISTS scoring_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id INTEGER NOT NULL,
    item_key TEXT UNIQUE NOT NULL,
    item_name TEXT NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    score_min REAL DEFAULT 1.0,
    score_max REAL DEFAULT 5.0,
    rule_json TEXT, -- JSON string for scoring rules
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (module_id) REFERENCES scoring_modules(id)
);

-- scoring_runs table (each analysis execution)
CREATE TABLE IF NOT EXISTS scoring_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_name TEXT,
    status TEXT DEFAULT 'pending', -- pending, completed, failed
    llm_model TEXT,
    total_score REAL,
    project_summary_json TEXT -- JSON string for Project Golden summary (industry, deal structure, risk)
);

-- scoring_results table (individual item scores)
CREATE TABLE IF NOT EXISTS scoring_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL,
    item_id INTEGER NOT NULL,
    extracted_value TEXT,
    evidence_text TEXT,
    score_raw REAL,
    score_weighted REAL,
    confidence REAL,
    notes TEXT,
    FOREIGN KEY (run_id) REFERENCES scoring_runs(id),
    FOREIGN KEY (item_id) REFERENCES scoring_items(id)
);
