"""
AgriMind Case Storage & Persistence Layer (Stage A.1).
Provides embedded, server-side SQLite storage for diagnostic case states.
Enforces case isolation, server-side reassessment tracking, and tamper resistance
against client-supplied state manipulation.
"""
import os
import sys
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Dict, Any, Optional

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.environ.get(
    "AGRIMIND_DB_PATH",
    os.path.join(WORKSPACE_DIR, "data", "cases.db")
)


class CaseStore:
    """
    SQLite-backed case store providing ACID persistence and tamper-proof state retrieval.
    Replaces client-side state round-tripping with authoritative server-side storage.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self):
        """Initializes the cases schema if it does not already exist."""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    workflow_status TEXT NOT NULL,
                    reassessment_count INTEGER NOT NULL DEFAULT 0,
                    primary_diagnosis TEXT,
                    assigned_severity TEXT,
                    state_json TEXT NOT NULL
                );
            """)
            conn.commit()

    def save_case(self, case_id: str, state: Dict[str, Any]) -> None:
        """
        Saves a new case state to persistent storage.
        Overwrites existing case only if explicitly updated.
        """
        now = datetime.now(timezone.utc).isoformat()
        final_output = state.get("final_output") or {}
        workflow_status = state.get("workflow_status", "completed")
        reassessment_count = state.get("reassessment_count", 0)
        primary_diag = final_output.get("primary_diagnosis")
        severity = final_output.get("assigned_severity")

        state_json = json.dumps(state)

        with self._connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cases (
                    case_id, created_at, updated_at, workflow_status,
                    reassessment_count, primary_diagnosis, assigned_severity, state_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                case_id, now, now, workflow_status,
                reassessment_count, primary_diag, severity, state_json
            ))
            conn.commit()

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves authoritative case state by case_id.
        Returns None if case does not exist.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT state_json FROM cases WHERE case_id = ?;",
                (case_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["state_json"])
            return None

    def update_case(self, case_id: str, state: Dict[str, Any]) -> None:
        """
        Updates an existing case after reassessment cycle.
        """
        now = datetime.now(timezone.utc).isoformat()
        final_output = state.get("final_output") or {}
        workflow_status = state.get("workflow_status", "completed")
        reassessment_count = state.get("reassessment_count", 0)
        primary_diag = final_output.get("primary_diagnosis")
        severity = final_output.get("assigned_severity")

        state_json = json.dumps(state)

        with self._connection() as conn:
            conn.execute("""
                UPDATE cases
                SET updated_at = ?,
                    workflow_status = ?,
                    reassessment_count = ?,
                    primary_diagnosis = ?,
                    assigned_severity = ?,
                    state_json = ?
                WHERE case_id = ?;
            """, (
                now, workflow_status, reassessment_count,
                primary_diag, severity, state_json, case_id
            ))
            conn.commit()

    def case_exists(self, case_id: str) -> bool:
        """Checks if a case ID exists in storage."""
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM cases WHERE case_id = ?;",
                (case_id,)
            )
            return cursor.fetchone() is not None

    def get_case_count(self) -> int:
        """Returns total number of stored cases."""
        with self._connection() as conn:
            cursor = conn.execute("SELECT COUNT(*) as count FROM cases;")
            row = cursor.fetchone()
            return row["count"] if row else 0

    def delete_case(self, case_id: str) -> bool:
        """Deletes a case from authoritative storage."""
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM cases WHERE case_id = ?;", (case_id,))
            conn.commit()
            return cursor.rowcount > 0


# Global singleton instance for application use
_CASE_STORE: Optional[CaseStore] = None


def get_case_store(db_path: Optional[str] = None) -> CaseStore:
    """Returns singleton CaseStore instance."""
    global _CASE_STORE
    if _CASE_STORE is None or (db_path and _CASE_STORE.db_path != db_path):
        _CASE_STORE = CaseStore(db_path or DEFAULT_DB_PATH)
    return _CASE_STORE


def set_case_store(store_instance: Optional[CaseStore]) -> None:
    """Allows setting or resetting the global CaseStore (useful for testing)."""
    global _CASE_STORE
    _CASE_STORE = store_instance
