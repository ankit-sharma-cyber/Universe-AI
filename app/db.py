"""SQLite persistence for sessions and conversation history.

Only auth sessions and chat history are persisted — event registrations,
calendar entries and reminders remain owned by the agent tools in memory.
"""

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "campus.db"

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    token       TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversations (
    id          TEXT PRIMARY KEY,
    student_id  TEXT NOT NULL,
    title       TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,
    content         TEXT NOT NULL,
    intent          TEXT,
    trace           TEXT,
    created_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS submissions (
    student_id    TEXT NOT NULL,
    assignment_id TEXT NOT NULL,
    submitted_at  TEXT NOT NULL,
    status        TEXT NOT NULL,
    PRIMARY KEY (student_id, assignment_id)
);

CREATE INDEX IF NOT EXISTS idx_conversations_student ON conversations(student_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id, id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect() -> sqlite3.Connection:
    """One connection per thread — FastAPI's threadpool reuses worker threads."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _local.conn = conn
    return conn


def init() -> None:
    connect().executescript(SCHEMA)
    connect().commit()


# ---------- sessions ----------

def create_session(student_id: str) -> str:
    token = uuid.uuid4().hex
    conn = connect()
    conn.execute(
        "INSERT INTO sessions (token, student_id, created_at) VALUES (?, ?, ?)",
        (token, student_id, _now()),
    )
    conn.commit()
    return token


def student_for_token(token: str) -> str | None:
    row = connect().execute("SELECT student_id FROM sessions WHERE token = ?", (token,)).fetchone()
    return row["student_id"] if row else None


def delete_session(token: str) -> None:
    conn = connect()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


# ---------- conversations ----------

def create_conversation(student_id: str, title: str) -> str:
    conv_id = uuid.uuid4().hex
    now = _now()
    conn = connect()
    conn.execute(
        "INSERT INTO conversations (id, student_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, student_id, title[:120], now, now),
    )
    conn.commit()
    return conv_id


def list_conversations(student_id: str) -> list[dict]:
    rows = connect().execute(
        """
        SELECT c.id, c.title, c.created_at, c.updated_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id) AS message_count
        FROM conversations c
        WHERE c.student_id = ?
        ORDER BY c.updated_at DESC
        """,
        (student_id,),
    ).fetchall()
    return [dict(row) for row in rows]


def owns_conversation(student_id: str, conversation_id: str) -> bool:
    row = connect().execute(
        "SELECT 1 FROM conversations WHERE id = ? AND student_id = ?", (conversation_id, student_id)
    ).fetchone()
    return row is not None


def delete_conversation(student_id: str, conversation_id: str) -> bool:
    conn = connect()
    cur = conn.execute(
        "DELETE FROM conversations WHERE id = ? AND student_id = ?", (conversation_id, student_id)
    )
    conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    conn.commit()
    return cur.rowcount > 0


def add_message(
    conversation_id: str,
    role: str,
    content: str,
    intent: str | None = None,
    trace: list[dict] | None = None,
) -> None:
    conn = connect()
    conn.execute(
        """
        INSERT INTO messages (conversation_id, role, content, intent, trace, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, role, content, intent, json.dumps(trace) if trace else None, _now()),
    )
    conn.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (_now(), conversation_id))
    conn.commit()


# ---------- assignment submissions ----------

def record_submission(student_id: str, assignment_id: str, status: str) -> dict:
    """Hand work in. Idempotent — re-submitting keeps the original timestamp."""
    conn = connect()
    conn.execute(
        """
        INSERT INTO submissions (student_id, assignment_id, submitted_at, status)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(student_id, assignment_id) DO NOTHING
        """,
        (student_id, assignment_id, _now(), status),
    )
    conn.commit()
    row = conn.execute(
        "SELECT submitted_at, status FROM submissions WHERE student_id = ? AND assignment_id = ?",
        (student_id, assignment_id),
    ).fetchone()
    return dict(row)


def submissions_for(student_id: str) -> dict[str, dict]:
    rows = connect().execute(
        "SELECT assignment_id, submitted_at, status FROM submissions WHERE student_id = ?",
        (student_id,),
    ).fetchall()
    return {row["assignment_id"]: dict(row) for row in rows}


def load_messages(conversation_id: str) -> list[dict]:
    rows = connect().execute(
        "SELECT role, content, intent, trace, created_at FROM messages WHERE conversation_id = ? ORDER BY id",
        (conversation_id,),
    ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["trace"] = json.loads(item["trace"]) if item["trace"] else []
        out.append(item)
    return out
