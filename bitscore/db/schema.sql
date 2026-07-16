PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS projects (
    project_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('file','folder')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS versions (
    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(project_id),
    version_number INTEGER NOT NULL,
    stored_filename TEXT NOT NULL UNIQUE,
    telegram_msg_id INTEGER,
    telegram_chat_id INTEGER,
    upload_date TEXT NOT NULL,
    upload_time TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    sha256_hash TEXT NOT NULL,
    upload_status TEXT NOT NULL CHECK (upload_status IN ('pending','uploaded','failed','deleted')),
    source_path TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_versions_project_id ON versions(project_id);
CREATE INDEX IF NOT EXISTS idx_versions_upload_date ON versions(upload_date);
CREATE INDEX IF NOT EXISTS idx_versions_status ON versions(upload_status);

CREATE TABLE IF NOT EXISTS sync_state (
    chat_id INTEGER PRIMARY KEY,
    last_message_id INTEGER NOT NULL,
    last_synced_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ignore_rules (
    rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern TEXT NOT NULL UNIQUE,
    enabled INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS plate_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    kind TEXT NOT NULL CHECK (kind IN ('file','folder')),
    added_at TEXT NOT NULL,
    estimated_size_bytes INTEGER
);

CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta(key, value) VALUES ('schema_version', '1');
