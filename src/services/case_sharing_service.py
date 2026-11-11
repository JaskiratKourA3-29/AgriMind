"""
AgriMind Authorized Farmer-to-Farmer & Cooperative Case Sharing Service.
Provides cryptographic token-based access controls, PII anonymization,
and SQLite persistence for collaborative disease intelligence.
"""

import os
import sys
import json
import uuid
import secrets
import sqlite3
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import contextmanager

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.environ.get(
    "AGRIMIND_DB_PATH",
    os.path.join(WORKSPACE_DIR, "data", "cases.db")
)

logger = logging.getLogger(__name__)


class CaseSharingService:
    """Manages authorized case sharing with access control tokens and privacy safeguards."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        if self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS shared_cases (
                    share_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    owner_farmer_id TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    access_level TEXT NOT NULL,
                    anonymize_pii INTEGER NOT NULL DEFAULT 1,
                    share_token TEXT NOT NULL,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    shared_data_json TEXT NOT NULL
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_target ON shared_cases(target_entity);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_shared_case ON shared_cases(case_id);")

            # Community comments / farmer observations table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_comments (
                    comment_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    author_id TEXT NOT NULL,
                    author_role TEXT NOT NULL DEFAULT 'farmer',
                    comment_text TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    is_ai INTEGER NOT NULL DEFAULT 0
                );
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_comments_case ON case_comments(case_id);")

            # Treatment outcome tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS case_outcomes (
                    case_id TEXT PRIMARY KEY,
                    farmer_id TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    details TEXT,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.commit()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def share_case(
        self,
        case_data: Dict[str, Any],
        owner_farmer_id: str,
        target_entity: str = "cooperative_all",
        access_level: str = "cooperative",
        anonymize_pii: bool = True,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Authorizes and shares a case with a target farmer or cooperative pool.
        Applies PII masking if anonymize_pii is True.
        """
        case_id = case_data.get("case_id", f"CASE-{uuid.uuid4().hex[:8].upper()}")
        share_id = f"SHARE-{uuid.uuid4().hex[:8].upper()}"
        share_token = f"tok_{secrets.token_urlsafe(16)}"
        created_at = datetime.now(timezone.utc).isoformat()

        # Build sanitized/anonymized payload
        sanitized_data = self._anonymize_case(case_data, owner_farmer_id, anonymize_pii)

        with self._connection() as conn:
            conn.execute("""
                INSERT INTO shared_cases (
                    share_id, case_id, owner_farmer_id, target_entity,
                    access_level, anonymize_pii, share_token, notes,
                    created_at, status, shared_data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)
            """, (
                share_id,
                case_id,
                owner_farmer_id,
                target_entity,
                access_level,
                1 if anonymize_pii else 0,
                share_token,
                notes or "",
                created_at,
                json.dumps(sanitized_data)
            ))
            conn.commit()

        return {
            "share_id": share_id,
            "case_id": case_id,
            "owner_farmer_id": "ANONYMOUS" if anonymize_pii else owner_farmer_id,
            "target_entity": target_entity,
            "access_level": access_level,
            "share_token": share_token,
            "anonymize_pii": anonymize_pii,
            "notes": notes,
            "created_at": created_at,
            "status": "active"
        }

    def get_shared_case(
        self,
        share_id: str,
        share_token: Optional[str] = None,
        requester_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a shared case if authorized via token or matching requester."""
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM shared_cases WHERE share_id = ? AND status = 'active'",
                (share_id,)
            ).fetchone()

            if not row:
                return None

            # Authorization check
            is_token_valid = (share_token is not None and secrets.compare_digest(row["share_token"], share_token))
            is_target_match = (
                requester_id is not None and (
                    row["target_entity"] == "cooperative_all" or
                    row["target_entity"] == requester_id or
                    row["owner_farmer_id"] == requester_id
                )
            )

            # Cooperative public shares can be read if target_entity is cooperative_all
            is_coop_public = (row["target_entity"] == "cooperative_all" and row["access_level"] == "cooperative")

            if not (is_token_valid or is_target_match or is_coop_public):
                return None

            data = json.loads(row["shared_data_json"])
            return {
                "share_id": row["share_id"],
                "case_id": row["case_id"],
                "target_entity": row["target_entity"],
                "access_level": row["access_level"],
                "created_at": row["created_at"],
                "notes": row["notes"],
                "case_data": data
            }

    def list_shared_cases(
        self,
        target_entity: str = "cooperative_all",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Lists active shared cases available to a specific cooperative pool or farmer."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT share_id, case_id, owner_farmer_id, target_entity,
                       access_level, anonymize_pii, notes, created_at, shared_data_json
                FROM shared_cases
                WHERE status = 'active' AND (target_entity = ? OR target_entity = 'cooperative_all')
                ORDER BY created_at DESC
                LIMIT ?
            """, (target_entity, limit)).fetchall()

            results = []
            for r in rows:
                data = json.loads(r["shared_data_json"])
                results.append({
                    "share_id": r["share_id"],
                    "case_id": r["case_id"],
                    "target_entity": r["target_entity"],
                    "access_level": r["access_level"],
                    "created_at": r["created_at"],
                    "notes": r["notes"],
                    "case_summary": {
                        "primary_diagnosis": data.get("primary_diagnosis"),
                        "confidence": data.get("confidence"),
                        "assigned_severity": data.get("assigned_severity"),
                        "epidemic_risk": data.get("epidemic_risk"),
                        "weather_summary": data.get("weather_summary"),
                        "region": data.get("region", "Regional Farm Pool")
                    }
                })
            return results

    def revoke_share(self, share_id: str, owner_farmer_id: str) -> bool:
        """Revokes access to a shared case. Only the owner can revoke."""
        with self._connection() as conn:
            cursor = conn.execute("""
                UPDATE shared_cases
                SET status = 'revoked'
                WHERE share_id = ? AND owner_farmer_id = ?
            """, (share_id, owner_farmer_id))
            conn.commit()
            return cursor.rowcount > 0

    def add_comment(
        self,
        case_id: str,
        author_id: str,
        comment_text: str,
        author_role: str = "farmer",
        is_ai: bool = False
    ) -> Dict[str, Any]:
        """
        Adds a comment or community observation to a case.
        Strictly records whether the contribution is from a human farmer or AI system.
        """
        comment_id = f"CMT-{uuid.uuid4().hex[:8].upper()}"
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO case_comments (
                    comment_id, case_id, author_id, author_role, comment_text, created_at, is_ai
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (comment_id, case_id, author_id, author_role, comment_text, created_at, 1 if is_ai else 0))
            conn.commit()

        return {
            "comment_id": comment_id,
            "case_id": case_id,
            "author_id": author_id,
            "author_role": author_role,
            "comment_text": comment_text,
            "created_at": created_at,
            "is_ai": is_ai
        }

    def get_comments(self, case_id: str) -> List[Dict[str, Any]]:
        """Retrieves all community comments and observations for a case in chronological order."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT comment_id, case_id, author_id, author_role, comment_text, created_at, is_ai
                FROM case_comments
                WHERE case_id = ?
                ORDER BY created_at ASC
            """, (case_id,)).fetchall()
            return [
                {
                    "comment_id": r["comment_id"],
                    "case_id": r["case_id"],
                    "author_id": r["author_id"],
                    "author_role": r["author_role"],
                    "comment_text": r["comment_text"],
                    "created_at": r["created_at"],
                    "is_ai": bool(r["is_ai"])
                }
                for r in rows
            ]

    def record_outcome(
        self,
        case_id: str,
        farmer_id: str,
        outcome: str,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records or updates a treatment outcome report for a case.
        Valid outcomes: 'helped', 'did_not_help', 'pending'
        """
        valid_outcomes = {"helped", "did_not_help", "pending"}
        norm_outcome = outcome.lower().strip()
        if norm_outcome not in valid_outcomes:
            norm_outcome = "pending"

        updated_at = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO case_outcomes (case_id, farmer_id, outcome, details, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(case_id) DO UPDATE SET
                    farmer_id = excluded.farmer_id,
                    outcome = excluded.outcome,
                    details = excluded.details,
                    updated_at = excluded.updated_at
            """, (case_id, farmer_id, norm_outcome, details or "", updated_at))
            conn.commit()

        return {
            "case_id": case_id,
            "farmer_id": farmer_id,
            "outcome": norm_outcome,
            "details": details or "",
            "updated_at": updated_at
        }

    def get_outcome(self, case_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves the recorded treatment outcome for a case, if any."""
        with self._connection() as conn:
            row = conn.execute("""
                SELECT case_id, farmer_id, outcome, details, updated_at
                FROM case_outcomes
                WHERE case_id = ?
            """, (case_id,)).fetchone()
            if not row:
                return None
            return {
                "case_id": row["case_id"],
                "farmer_id": row["farmer_id"],
                "outcome": row["outcome"],
                "details": row["details"],
                "updated_at": row["updated_at"]
            }

    def _anonymize_case(
        self,
        case_data: Dict[str, Any],
        owner_farmer_id: str,
        anonymize: bool
    ) -> Dict[str, Any]:
        """Strips farmer identifying info and fuzzes GPS coordinates if anonymized."""
        base = dict(case_data)
        if not anonymize:
            base["owner_farmer_id"] = owner_farmer_id
            return base

        # Anonymize PII
        base["owner_farmer_id"] = f"FARMER-{abs(hash(owner_farmer_id)) % 10000:04d}"
        if "farmer_name" in base:
            base["farmer_name"] = "Anonymous Farmer"
        if "phone" in base:
            del base["phone"]
        if "email" in base:
            del base["email"]

        # Fuzz GPS coordinates to ~11 km regional radius (1 decimal place)
        if "latitude" in base and base["latitude"] is not None:
            base["latitude"] = round(float(base["latitude"]), 1)
        if "longitude" in base and base["longitude"] is not None:
            base["longitude"] = round(float(base["longitude"]), 1)
        base["region"] = "Regional Cooperative Grid"

        return base


# Singleton
_CASE_SHARING_SERVICE = None


def get_case_sharing_service() -> CaseSharingService:
    global _CASE_SHARING_SERVICE
    if _CASE_SHARING_SERVICE is None:
        _CASE_SHARING_SERVICE = CaseSharingService()
    return _CASE_SHARING_SERVICE

