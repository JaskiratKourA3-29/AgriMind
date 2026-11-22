"""
AgriMind Case Storage & Persistence Layer (Stage A.1 & Cloud Upgrade).
Provides hybrid SQLite and Neon PostgreSQL storage for diagnostic case states.
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
from src.services.db_pool import get_db_connection

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.environ.get(
    "DATABASE_URL",
    os.environ.get("AGRIMIND_DB_URL", os.path.join(WORKSPACE_DIR, "data", "cases.db"))
)


class CaseStore:
    """
    Hybrid PostgreSQL / SQLite case store providing ACID persistence and tamper-proof state retrieval.
    Replaces client-side state round-tripping with authoritative server-side storage.
    Supports Neon Serverless PostgreSQL when DATABASE_URL is configured, with seamless SQLite fallback.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.is_postgres = str(db_path).startswith("postgres://") or str(db_path).startswith("postgresql://")
        if self.is_postgres and not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL database URL specified, but 'psycopg2' is not installed.")
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        if not self.is_postgres and self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    def _format_sql(self, sql: str) -> str:
        """Adapts %s placeholders to ? when running against local SQLite."""
        if self.is_postgres:
            return sql
        return sql.replace("%s", "?")

    @contextmanager
    def _connection(self):
        with get_db_connection(self.db_path) as conn:
            yield conn

    def _execute(self, conn, sql: str, params: tuple = ()):
        """Executes a parameterized query with engine-specific placeholder translation."""
        formatted_sql = self._format_sql(sql)
        if self.is_postgres:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cursor = conn.cursor()
        cursor.execute(formatted_sql, params)
        return cursor

    def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        """Checks if a column exists in a table in an engine-safe manner without aborting transactions."""
        if self.is_postgres:
            cur = self._execute(conn, """
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = current_schema() 
                  AND table_name = %s 
                  AND column_name = %s;
            """, (table_name, column_name))
            return bool(cur.fetchone())
        else:
            cur = self._execute(conn, f'PRAGMA table_info("{table_name}");')
            cols = [row[1] if isinstance(row, (tuple, list)) else row["name"] for row in cur.fetchall()]
            return column_name in cols

    def _init_db(self):
        """Initializes the cases schema if it does not already exist."""
        with self._connection() as conn:
            self._execute(conn, """
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    workflow_status TEXT NOT NULL,
                    reassessment_count INTEGER NOT NULL DEFAULT 0,
                    primary_diagnosis TEXT,
                    assigned_severity TEXT,
                    state_json TEXT NOT NULL,
                    owner_user_id TEXT
                );
            """)
            # Safe column addition if upgrading existing table (check existence first to prevent aborted transactions)
            if not self._column_exists(conn, "cases", "owner_user_id"):
                self._execute(conn, "ALTER TABLE cases ADD COLUMN owner_user_id TEXT;")

    def save_case(self, case_id: str, state: Dict[str, Any], owner_user_id: Optional[str] = None) -> None:
        """
        Saves a new case state to persistent storage.
        Overwrites existing case only if explicitly updated, preserving or updating owner_user_id.
        """
        now = datetime.now(timezone.utc).isoformat()
        final_output = state.get("final_output") or {}
        workflow_status = state.get("workflow_status", "completed")
        reassessment_count = state.get("reassessment_count", 0)
        primary_diag = final_output.get("primary_diagnosis")
        severity = final_output.get("assigned_severity")

        state_json = json.dumps(state)

        with self._connection() as conn:
            self._execute(conn, """
                INSERT INTO cases (
                    case_id, created_at, updated_at, workflow_status,
                    reassessment_count, primary_diagnosis, assigned_severity, state_json, owner_user_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (case_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at,
                    workflow_status = EXCLUDED.workflow_status,
                    reassessment_count = EXCLUDED.reassessment_count,
                    primary_diagnosis = EXCLUDED.primary_diagnosis,
                    assigned_severity = EXCLUDED.assigned_severity,
                    state_json = EXCLUDED.state_json,
                    owner_user_id = COALESCE(EXCLUDED.owner_user_id, cases.owner_user_id);
            """, (
                case_id, now, now, workflow_status,
                reassessment_count, primary_diag, severity, state_json, owner_user_id
            ))

    def get_case(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves authoritative case state by case_id.
        Returns None if case does not exist.
        """
        with self._connection() as conn:
            cursor = self._execute(
                conn,
                "SELECT state_json FROM cases WHERE case_id = %s;",
                (case_id,)
            )
            row = cursor.fetchone()
            if row:
                raw_json = row["state_json"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]
                return json.loads(raw_json)
            return None

    def get_case_record(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves full case record including owner_user_id for access authorization.
        """
        with self._connection() as conn:
            cursor = self._execute(
                conn,
                "SELECT case_id, created_at, updated_at, workflow_status, reassessment_count, primary_diagnosis, assigned_severity, owner_user_id, state_json FROM cases WHERE case_id = %s;",
                (case_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["state"] = json.loads(d["state_json"])
            return d

    def update_case(self, case_id: str, state: Dict[str, Any], owner_user_id: Optional[str] = None) -> None:
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
            if owner_user_id:
                self._execute(conn, """
                    UPDATE cases
                    SET updated_at = %s,
                        workflow_status = %s,
                        reassessment_count = %s,
                        primary_diagnosis = %s,
                        assigned_severity = %s,
                        state_json = %s,
                        owner_user_id = %s
                    WHERE case_id = %s;
                """, (
                    now, workflow_status, reassessment_count,
                    primary_diag, severity, state_json, owner_user_id, case_id
                ))
            else:
                self._execute(conn, """
                    UPDATE cases
                    SET updated_at = %s,
                        workflow_status = %s,
                        reassessment_count = %s,
                        primary_diagnosis = %s,
                        assigned_severity = %s,
                        state_json = %s
                    WHERE case_id = %s;
                """, (
                    now, workflow_status, reassessment_count,
                    primary_diag, severity, state_json, case_id
                ))

    def case_exists(self, case_id: str) -> bool:
        """Checks if a case ID exists in storage."""
        with self._connection() as conn:
            cursor = self._execute(
                conn,
                "SELECT 1 FROM cases WHERE case_id = %s;",
                (case_id,)
            )
            return cursor.fetchone() is not None

    def get_case_count(self) -> int:
        """Returns total number of stored cases."""
        with self._connection() as conn:
            cursor = self._execute(conn, "SELECT COUNT(*) as count FROM cases;")
            row = cursor.fetchone()
            if not row:
                return 0
            return row["count"] if isinstance(row, dict) or hasattr(row, "__getitem__") else row[0]

    def delete_case(self, case_id: str) -> bool:
        """Deletes a case from authoritative storage."""
        with self._connection() as conn:
            cursor = self._execute(conn, "DELETE FROM cases WHERE case_id = %s;", (case_id,))
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
