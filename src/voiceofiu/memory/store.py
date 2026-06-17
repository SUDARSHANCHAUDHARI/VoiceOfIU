"""SQLite persistence for all conversation turns and meal logs."""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.expanduser("~/.local/share/VoiceOfIU/memory.db")


def init():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS turns (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                role      TEXT NOT NULL,
                content   TEXT NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS turns_fts
                USING fts5(content, content='turns', content_rowid='id');
            CREATE TRIGGER IF NOT EXISTS turns_ai AFTER INSERT ON turns BEGIN
                INSERT INTO turns_fts(rowid, content) VALUES (new.id, new.content);
            END;
            CREATE TABLE IF NOT EXISTS meals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT NOT NULL,
                description TEXT NOT NULL,
                calories    INTEGER
            );
        """)


def save_turn(role: str, content: str):
    content = _redact(content)
    with _conn() as conn:
        conn.execute(
            "INSERT INTO turns (timestamp, role, content) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), role, content),
        )


def _redact(text: str) -> str:
    """Strip secrets before persisting — keeps the memory DB free of credentials."""
    try:
        from ..tools import redact as _r
        return _r.redact(text)
    except Exception:
        return text


def search_turns(query: str, limit: int = 5) -> list[dict]:
    fts_query = _to_fts_query(query)
    if not fts_query:
        return []
    try:
        with _conn() as conn:
            rows = conn.execute("""
                SELECT t.timestamp, t.role, t.content
                FROM turns_fts
                JOIN turns t ON turns_fts.rowid = t.id
                WHERE turns_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            """, (fts_query, limit)).fetchall()
        return [{"timestamp": r[0], "role": r[1], "content": r[2]} for r in rows]
    except Exception:
        return []


def _to_fts_query(text: str) -> str:
    """Strip FTS5 special chars, keep plain words only."""
    import re
    words = re.sub(r"[^\w\s]", " ", text).split()[:8]
    return " ".join(words)


def get_recent_turns(limit: int = 40) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT timestamp, role, content FROM turns ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
    return [{"timestamp": r[0], "role": r[1], "content": r[2]} for r in reversed(rows)]


def get_turns_older_than(days: int) -> list[dict]:
    """Return non-summary turns older than `days`, oldest first."""
    with _conn() as conn:
        rows = conn.execute("""
            SELECT timestamp, role, content FROM turns
            WHERE timestamp < datetime('now', ?) AND role != 'summary'
            ORDER BY id ASC
        """, (f"-{days} days",)).fetchall()
    return [{"timestamp": r[0], "role": r[1], "content": r[2]} for r in rows]


def delete_turns_before(cutoff_iso: str, keep_summaries: bool = True):
    """Delete turns with timestamp before cutoff. Optionally keep summary rows."""
    with _conn() as conn:
        if keep_summaries:
            conn.execute(
                "DELETE FROM turns WHERE timestamp < ? AND role != 'summary'",
                (cutoff_iso,),
            )
        else:
            conn.execute("DELETE FROM turns WHERE timestamp < ?", (cutoff_iso,))


def save_meal(description: str, calories: int | None = None):
    with _conn() as conn:
        conn.execute(
            "INSERT INTO meals (timestamp, description, calories) VALUES (?, ?, ?)",
            (datetime.now().isoformat(), description, calories),
        )


def get_meals(days: int = 7) -> list[dict]:
    with _conn() as conn:
        rows = conn.execute("""
            SELECT timestamp, description, calories FROM meals
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        """, (f"-{days} days",)).fetchall()
    return [{"timestamp": r[0], "description": r[1], "calories": r[2]} for r in rows]


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
