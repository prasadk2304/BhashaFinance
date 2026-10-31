import json
import sqlite3
from typing import Optional
from backend.config import settings
from backend.state import JourneyState


_db_initialized = False

def get_db_connection() -> sqlite3.Connection:
    global _db_initialized
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    if not _db_initialized:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                journey_id TEXT NOT NULL,
                status TEXT NOT NULL,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS consent_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                journey_id TEXT NOT NULL,
                consent_granted INTEGER NOT NULL,
                consent_text TEXT,
                method TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        conn.commit()
        _db_initialized = True
    return conn


def init_db():
    """Initializes SQLite tables for session states and consent audit trails."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            journey_id TEXT NOT NULL,
            status TEXT NOT NULL,
            state_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consent_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            journey_id TEXT NOT NULL,
            consent_granted INTEGER NOT NULL,
            consent_text TEXT,
            method TEXT,
            timestamp TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
        )
    """)

    conn.commit()
    conn.close()


def save_state(state: JourneyState):
    """Persists current JourneyState to SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    state_json = state.model_dump_json()

    cursor.execute("""
        INSERT INTO sessions (session_id, journey_id, status, state_json, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            journey_id=excluded.journey_id,
            status=excluded.status,
            state_json=excluded.state_json,
            updated_at=excluded.updated_at
    """, (
        state.session_id,
        state.journey_id,
        state.status.value,
        state_json,
        state.created_at,
        state.updated_at,
    ))

    # If consent was granted, record audit entry
    if state.consent.granted:
        cursor.execute("""
            INSERT INTO consent_audit_log (session_id, journey_id, consent_granted, consent_text, method, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            state.session_id,
            state.journey_id,
            1,
            state.consent.consent_text,
            state.consent.method,
            state.consent.granted_at or state.updated_at,
        ))

    conn.commit()
    conn.close()


def load_state(session_id: str) -> Optional[JourneyState]:
    """Loads JourneyState from SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT state_json FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()

    if row:
        data = json.loads(row["state_json"])
        return JourneyState.model_validate(data)
    return None
