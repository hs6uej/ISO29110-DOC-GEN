"""SQLite persistence (data/app.db)."""
import json
import sqlite3
from contextlib import contextmanager

from . import settings

DB_PATH = settings.DATA_DIR / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    code        TEXT NOT NULL UNIQUE,
    customer    TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    facts       TEXT NOT NULL DEFAULT '{}',
    created_at  TEXT DEFAULT (datetime('now','localtime')),
    updated_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    stage       TEXT NOT NULL,
    role        TEXT NOT NULL,          -- 'assistant' | 'user'
    content     TEXT NOT NULL,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS documents (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id   INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    doc_key      TEXT NOT NULL,
    item_index   INTEGER,
    filename     TEXT NOT NULL,
    rel_path     TEXT NOT NULL,
    version      TEXT NOT NULL,
    placeholders INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS users (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    email          TEXT NOT NULL UNIQUE,
    name           TEXT NOT NULL,
    position       TEXT NOT NULL DEFAULT '',
    phone          TEXT NOT NULL DEFAULT '',
    password_hash  TEXT NOT NULL,
    role           TEXT NOT NULL DEFAULT 'editor',   -- admin | editor | viewer
    status         TEXT NOT NULL DEFAULT 'pending',  -- active | pending | disabled
    created_at     TEXT DEFAULT (datetime('now','localtime')),
    last_login_at  TEXT,
    last_login_ip  TEXT,
    last_seen_at   TEXT
);
CREATE TABLE IF NOT EXISTS sessions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash    TEXT NOT NULL UNIQUE,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ip            TEXT NOT NULL DEFAULT '',
    user_agent    TEXT NOT NULL DEFAULT '',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    last_seen_at  TEXT,
    expires_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activity_logs (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ts             TEXT DEFAULT (datetime('now','localtime')),
    user_id        INTEGER,
    user_email     TEXT NOT NULL DEFAULT '',
    user_name      TEXT NOT NULL DEFAULT '',
    ip             TEXT NOT NULL DEFAULT '',
    forwarded_for  TEXT NOT NULL DEFAULT '',
    user_agent     TEXT NOT NULL DEFAULT '',
    session_id     INTEGER,
    method         TEXT NOT NULL DEFAULT '',
    path           TEXT NOT NULL DEFAULT '',
    query          TEXT NOT NULL DEFAULT '',
    status         INTEGER,
    duration_ms    INTEGER,
    action         TEXT NOT NULL DEFAULT '',
    target         TEXT NOT NULL DEFAULT '',
    detail         TEXT NOT NULL DEFAULT '',
    body           TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_logs_ts ON activity_logs(ts);
CREATE INDEX IF NOT EXISTS ix_logs_user ON activity_logs(user_id);
CREATE INDEX IF NOT EXISTS ix_logs_action ON activity_logs(action);
CREATE TABLE IF NOT EXISTS evidence (
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    doc_key     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'missing',
    links       TEXT NOT NULL DEFAULT '',
    remark      TEXT NOT NULL DEFAULT '',
    updated_at  TEXT DEFAULT (datetime('now','localtime')),
    PRIMARY KEY (project_id, doc_key)
);
"""


# who-did-what columns added to tables created before user accounts existed
MIGRATIONS = {
    "users": {"username": "TEXT"},
    "projects": {"created_by": "INTEGER", "updated_by": "INTEGER"},
    "messages": {"user_id": "INTEGER"},
    "documents": {"created_by": "INTEGER", "source": "TEXT NOT NULL DEFAULT 'ai'"},
    "evidence": {"updated_by": "INTEGER"},
}


def init():
    with conn() as c:
        c.executescript(SCHEMA)
        for table, cols in MIGRATIONS.items():
            have = {r["name"] for r in c.execute(f"PRAGMA table_info({table})")}
            for col, decl in cols.items():
                if col not in have:
                    c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
        c.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users(username) WHERE username IS NOT NULL")


@contextmanager
def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def rows(sql, args=()):
    with conn() as c:
        return [dict(r) for r in c.execute(sql, args).fetchall()]


def row(sql, args=()):
    r = rows(sql, args)
    return r[0] if r else None


def execute(sql, args=()):
    with conn() as c:
        cur = c.execute(sql, args)
        return cur.lastrowid


def get_project(pid: int) -> dict | None:
    p = row("SELECT * FROM projects WHERE id=?", (pid,))
    if p:
        p["facts"] = json.loads(p["facts"] or "{}")
    return p


def save_facts(pid: int, facts: dict):
    execute(
        "UPDATE projects SET facts=?, updated_at=datetime('now','localtime') WHERE id=?",
        (json.dumps(facts, ensure_ascii=False), pid),
    )
