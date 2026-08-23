"""SQLite connection and schema migrations."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS articles (
    pmid TEXT PRIMARY KEY,
    title TEXT,
    authors_json TEXT NOT NULL,
    journal TEXT,
    publication_date TEXT,
    abstract TEXT,
    doi TEXT,
    pubmed_url TEXT NOT NULL,
    retrieved_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS search_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL REFERENCES research_questions(id),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    extractor_model TEXT,
    extractor_prompt_version TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS search_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id INTEGER NOT NULL REFERENCES search_runs(id),
    query TEXT NOT NULL,
    source TEXT NOT NULL,
    pmids_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    claim TEXT NOT NULL,
    pmid TEXT NOT NULL REFERENCES articles(pmid),
    question_id INTEGER REFERENCES research_questions(id),
    run_id INTEGER REFERENCES search_runs(id),
    source_title TEXT,
    source_url TEXT NOT NULL,
    publication_date TEXT,
    journal TEXT,
    doi TEXT,
    study_type TEXT,
    sample_size INTEGER,
    population TEXT,
    intervention TEXT,
    comparator TEXT,
    outcome TEXT,
    supporting_text TEXT NOT NULL,
    supporting_text_start INTEGER,
    supporting_text_end INTEGER,
    source_fields_used_json TEXT NOT NULL,
    limitations_json TEXT NOT NULL,
    evidence_strength TEXT NOT NULL,
    reasoning_note TEXT NOT NULL,
    abstract_limited INTEGER NOT NULL DEFAULT 1,
    extractor_model TEXT NOT NULL,
    extractor_prompt_version TEXT NOT NULL,
    validation_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    validated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_pmid ON evidence_records(pmid);
CREATE INDEX IF NOT EXISTS idx_evidence_question ON evidence_records(question_id);
CREATE INDEX IF NOT EXISTS idx_evidence_run ON evidence_records(run_id);
"""


def default_db_path() -> Path:
    """Default DB path: ECD_DB_PATH env, else ./data/ecd_research.db."""
    override = os.getenv("ECD_DB_PATH", "").strip()
    if override:
        return Path(override)
    return Path.cwd() / "data" / "ecd_research.db"


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Open SQLite with foreign keys enabled and initialize schema."""
    path = Path(db_path) if db_path is not None else default_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if missing and record schema version."""
    conn.executescript(SCHEMA_SQL)
    conn.execute(
        "INSERT INTO schema_meta(key, value) VALUES('version', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
