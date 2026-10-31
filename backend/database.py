import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional
import uuid
from backend.config import settings
from backend.planner import build_review_readiness
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                category TEXT NOT NULL,
                issue_description TEXT NOT NULL,
                resolution_plan TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_cases (
                review_case_id TEXT PRIMARY KEY,
                session_id TEXT UNIQUE NOT NULL,
                journey_id TEXT NOT NULL,
                status TEXT NOT NULL,
                packet_json TEXT NOT NULL,
                readiness_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_requests (
                request_id TEXT PRIMARY KEY,
                review_case_id TEXT NOT NULL,
                material_key TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(review_case_id) REFERENCES review_cases(review_case_id)
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_cases (
            review_case_id TEXT PRIMARY KEY,
            session_id TEXT UNIQUE NOT NULL,
            journey_id TEXT NOT NULL,
            status TEXT NOT NULL,
            packet_json TEXT NOT NULL,
            readiness_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS review_requests (
            request_id TEXT PRIMARY KEY,
            review_case_id TEXT NOT NULL,
            material_key TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(review_case_id) REFERENCES review_cases(review_case_id)
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

def save_ticket(ticket: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets (ticket_id, session_id, category, issue_description, resolution_plan, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        ticket["ticket_id"],
        ticket["session_id"],
        ticket.get("category", "support"),
        ticket.get("issue_description", ""),
        ticket.get("resolution_plan", ""),
        ticket.get("status", "open"),
        ticket.get("created_at", ""),
    ))
    conn.commit()
    conn.close()


def get_tickets_for_session(session_id: str) -> list[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE session_id = ?", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_review_case(state: JourneyState) -> dict:
    """Persist only the masked demo review packet for an explicitly consented handoff."""
    if not state.review_consent.granted:
        raise PermissionError("Explicit review-handoff consent is required.")

    init_db()
    now = datetime.now(timezone.utc).isoformat()
    review_case_id = state.review_case_id or f"REV-{uuid.uuid4().hex[:8].upper()}"
    readiness = build_review_readiness(state).model_dump()
    packet = {
        "session_id": state.session_id,
        "journey_id": state.journey_id,
        "fields": {name: field.model_dump() for name, field in state.fields.items()},
        "masked_previews": state.masked_previews,
        "document_checklist": [item.model_dump() for item in state.document_checklist],
        "review_consent": state.review_consent.model_dump(),
    }
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO review_cases (review_case_id, session_id, journey_id, status, packet_json, readiness_json, created_at, updated_at)
        VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
        ON CONFLICT(session_id) DO UPDATE SET
            packet_json=excluded.packet_json,
            readiness_json=excluded.readiness_json,
            updated_at=excluded.updated_at
        """,
        (review_case_id, state.session_id, state.journey_id, json.dumps(packet), json.dumps(readiness), now, now),
    )
    conn.commit()
    conn.close()
    state.review_case_id = review_case_id
    return get_review_case(review_case_id) or {}


def get_review_case(review_case_id: str) -> Optional[dict]:
    init_db()
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM review_cases WHERE review_case_id = ?", (review_case_id,)).fetchone()
    if not row:
        conn.close()
        return None
    requests = conn.execute(
        "SELECT material_key, message, created_at FROM review_requests WHERE review_case_id = ? ORDER BY created_at",
        (review_case_id,),
    ).fetchall()
    conn.close()
    case = dict(row)
    return {
        "review_case_id": case["review_case_id"],
        "session_id": case["session_id"],
        "journey_id": case["journey_id"],
        "status": case["status"],
        "packet": json.loads(case["packet_json"]),
        "readiness": json.loads(case["readiness_json"]),
        "created_at": case["created_at"],
        "material_requests": [dict(request) for request in requests],
    }


def get_review_case_for_session(session_id: str) -> Optional[dict]:
    init_db()
    conn = get_db_connection()
    row = conn.execute("SELECT review_case_id FROM review_cases WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return get_review_case(row["review_case_id"]) if row else None


def request_review_material(review_case_id: str, material_key: str, message: str) -> dict:
    init_db()
    case = get_review_case(review_case_id)
    if not case:
        raise ValueError("Review case not found.")
    now = datetime.now(timezone.utc).isoformat()
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO review_requests (request_id, review_case_id, material_key, message, created_at) VALUES (?, ?, ?, ?, ?)",
        (f"REQ-{uuid.uuid4().hex[:8].upper()}", review_case_id, material_key, message, now),
    )
    conn.execute("UPDATE review_cases SET status = 'material_requested', updated_at = ? WHERE review_case_id = ?", (now, review_case_id))
    conn.commit()
    conn.close()
    return get_review_case(review_case_id) or {}

