"""Audit trail, metrics, and saved opportunities."""

import sqlite3, os
DB_PATH = os.environ.get("DATABASE_PATH", "entrepreneur_agent.db")


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, skill_id TEXT,
            input_summary TEXT, output TEXT, created_at TEXT DEFAULT (datetime('now')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT, metric_key TEXT UNIQUE,
            metric_value INTEGER DEFAULT 0, updated_at TEXT DEFAULT (datetime('now')))""")
        c.execute("""CREATE TABLE IF NOT EXISTS opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, industry TEXT,
            problem TEXT, score INTEGER DEFAULT 0, stage TEXT DEFAULT 'idea',
            notes TEXT, created_at TEXT DEFAULT (datetime('now')))""")


def log_interaction(session_id: str, skill_id: str, user_input: str, output: str):
    with _conn() as c:
        c.execute("INSERT INTO audit_log (session_id,skill_id,input_summary,output) VALUES (?,?,?,?)",
                  (session_id, skill_id, user_input[:300], output))
        for key in (f"count_{skill_id}", "total"):
            c.execute("INSERT INTO metrics (metric_key,metric_value) VALUES (?,1) ON CONFLICT(metric_key) DO UPDATE SET metric_value=metric_value+1", (key,))


def save_opportunity(title: str, industry: str, problem: str, score: int = 0, notes: str = ""):
    with _conn() as c:
        c.execute("INSERT INTO opportunities (title,industry,problem,score,notes) VALUES (?,?,?,?,?)",
                  (title, industry, problem, score, notes))


def get_opportunities(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM opportunities ORDER BY score DESC, created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_audit_log(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [dict(r) for r in rows]


def get_metrics() -> dict:
    with _conn() as c:
        rows = c.execute("SELECT metric_key,metric_value FROM metrics").fetchall()
    return {r["metric_key"]: r["metric_value"] for r in rows}
