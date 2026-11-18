"""
AgriMind Authentication & Role Separation Service (Stage C & Upgrades).
Provides:
- User signup, login, session token management, and logout (token revocation).
- Cryptographically secure password hashing using PBKDF2-HMAC-SHA256 (100,000 iterations + per-user salt).
- Role-based authorization: 'farmer' vs 'admin' vs 'owner'.
- Immutable audit logging for security-sensitive operations.
- Tamper-proof HMAC-SHA256 signed session tokens.
- Cross-farmer record isolation and admin management capabilities.
- Owner bootstrap and governance safeguards (prevents accidental removal of last owner).
"""
import os
import sys
import json
import uuid
import hmac
import base64
import hashlib
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_DB_PATH = os.environ.get(
    "DATABASE_URL",
    os.environ.get("AGRIMIND_DB_URL", os.path.join(WORKSPACE_DIR, "data", "cases.db"))
)

# Secret key for HMAC token signing (can be overridden via environment variable)
AUTH_SECRET_KEY = os.environ.get("AGRIMIND_AUTH_SECRET", "agrimind-secure-auth-secret-key-2026-production")
TOKEN_TTL_HOURS = 24 * 7  # 7 days session lifetime
PBKDF2_ITERATIONS = 100_000


try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class DBConnectionWrapper:
    """
    Transparent connection wrapper enabling uniform parameterized query execution
    across Neon PostgreSQL (psycopg2) and local development / test SQLite instances.
    """
    def __init__(self, raw_conn, is_postgres: bool):
        self._conn = raw_conn
        self.is_postgres = is_postgres

    def execute(self, sql: str, params: tuple = ()):
        formatted_sql = sql.replace("?", "%s") if self.is_postgres else sql.replace("%s", "?")
        if self.is_postgres:
            cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            cur = self._conn.cursor()
        cur.execute(formatted_sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


class AuthService:
    """
    SQLite-backed authentication and user management service.
    Enforces role separation ('farmer' vs 'admin' vs 'owner') and farmer record privacy.
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH, secret_key: str = AUTH_SECRET_KEY):
        self.db_path = db_path
        self.secret_key = secret_key
        self.is_postgres = str(db_path).startswith("postgres://") or str(db_path).startswith("postgresql://")
        if self.is_postgres and not PSYCOPG2_AVAILABLE:
            raise RuntimeError("PostgreSQL database URL specified, but 'psycopg2' is not installed.")
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        if not self.is_postgres and self.db_path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    @contextmanager
    def _connection(self):
        if self.is_postgres:
            raw_conn = psycopg2.connect(self.db_path)
            raw_conn.autocommit = False
            wrapper = DBConnectionWrapper(raw_conn, is_postgres=True)
            try:
                yield wrapper
                wrapper.commit()
            except Exception:
                wrapper.rollback()
                raise
            finally:
                wrapper.close()
        else:
            raw_conn = sqlite3.connect(self.db_path, timeout=10.0)
            raw_conn.row_factory = sqlite3.Row
            wrapper = DBConnectionWrapper(raw_conn, is_postgres=False)
            try:
                yield wrapper
                wrapper.commit()
            except Exception:
                wrapper.rollback()
                raise
            finally:
                wrapper.close()

    def _table_exists(self, conn, table_name: str) -> bool:
        """Checks if a table exists in an engine-safe manner without aborting transactions."""
        if self.is_postgres:
            cur = conn.execute("""
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = current_schema() AND table_name = %s;
            """, (table_name,))
            return bool(cur.fetchone())
        else:
            cur = conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name = ?;", (table_name,))
            return bool(cur.fetchone())

    def _column_exists(self, conn, table_name: str, column_name: str) -> bool:
        """Checks if a column exists in a table in an engine-safe manner without aborting transactions."""
        if self.is_postgres:
            cur = conn.execute("""
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = current_schema() 
                  AND table_name = %s 
                  AND column_name = %s;
            """, (table_name, column_name))
            return bool(cur.fetchone())
        else:
            if not self._table_exists(conn, table_name):
                return False
            cur = conn.execute(f'PRAGMA table_info("{table_name}");')
            cols = [row[1] for row in cur.fetchall()]
            return column_name in cols

    def _init_db(self):
        """Initializes users, token revocation, and audit logs tables."""
        with self._connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('farmer', 'admin', 'owner', 'sub_owner')),
                    phone TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sub_owner_permissions (
                    user_id TEXT PRIMARY KEY,
                    permissions_json TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS revoked_tokens (
                    token_jti TEXT PRIMARY KEY,
                    revoked_at TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    log_id TEXT PRIMARY KEY,
                    actor_id TEXT NOT NULL,
                    actor_email TEXT NOT NULL,
                    actor_role TEXT NOT NULL,
                    target_user_id TEXT,
                    action TEXT NOT NULL,
                    details TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                );
            """)
            # Safe column additions if upgrading existing schema (check existence first to prevent aborted transactions)
            if self._table_exists(conn, "cases") and not self._column_exists(conn, "cases", "owner_user_id"):
                conn.execute("ALTER TABLE cases ADD COLUMN owner_user_id TEXT;")
            if not self._column_exists(conn, "users", "updated_at"):
                conn.execute("ALTER TABLE users ADD COLUMN updated_at TEXT;")

            conn.commit()

    # =========================================================================
    # Cryptographic Password Utilities
    # =========================================================================

    @staticmethod
    def _hash_password(password: str, salt: str) -> str:
        """Derives a secure 256-bit hash using PBKDF2-HMAC-SHA256."""
        derived = hashlib.pbkdf2_hmac(
            hash_name="sha256",
            password=password.encode("utf-8"),
            salt=salt.encode("utf-8"),
            iterations=PBKDF2_ITERATIONS
        )
        return derived.hex()

    def _verify_password(self, password: str, salt: str, expected_hash: str) -> bool:
        """Constant-time password hash comparison to prevent timing attacks."""
        computed = self._hash_password(password, salt)
        return hmac.compare_digest(computed, expected_hash)

    # =========================================================================
    # Audit Logging
    # =========================================================================

    def log_audit_event(
        self,
        actor_id: str,
        actor_email: str,
        actor_role: str,
        action: str,
        details: str,
        target_user_id: Optional[str] = None
    ) -> str:
        """Records an immutable security audit event."""
        log_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                INSERT INTO audit_logs (log_id, actor_id, actor_email, actor_role, target_user_id, action, details, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (log_id, actor_id, actor_email, actor_role, target_user_id, action, details, now))
            conn.commit()
        return log_id

    # =========================================================================
    # Token Creation & Verification
    # =========================================================================

    def create_token(self, user_id: str, email: str, role: str) -> str:
        """
        Generates a tamper-proof signed session token containing claims and HMAC-SHA256 signature.
        Format: base64(header).base64(payload).base64(signature)
        """
        jti = uuid.uuid4().hex
        exp = (datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "jti": jti,
            "exp": exp,
            "iat": datetime.now(timezone.utc).timestamp()
        }

        b64_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        b64_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        signing_input = f"{b64_header}.{b64_payload}".encode("utf-8")
        sig = hmac.new(self.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
        b64_sig = base64.urlsafe_b64encode(sig).decode().rstrip("=")

        return f"{b64_header}.{b64_payload}.{b64_sig}"

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verifies signature, expiration, and revocation status of a token.
        Returns decoded claims if valid, else None.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            b64_header, b64_payload, b64_sig = parts

            # Re-compute signature
            signing_input = f"{b64_header}.{b64_payload}".encode("utf-8")
            expected_sig = hmac.new(self.secret_key.encode("utf-8"), signing_input, hashlib.sha256).digest()
            expected_b64_sig = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

            if not hmac.compare_digest(b64_sig, expected_b64_sig):
                return None

            # Decode payload with padding
            rem = len(b64_payload) % 4
            padded = b64_payload + ("=" * (4 - rem) if rem else "")
            payload = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())

            # Check expiration
            exp = payload.get("exp", 0)
            if datetime.now(timezone.utc).timestamp() > exp:
                return None

            # Check revocation
            jti = payload.get("jti")
            if jti and self._is_token_revoked(jti):
                return None

            return payload
        except Exception:
            return None

    def revoke_token(self, token: str) -> bool:
        """Marks a token's JTI as revoked in persistent storage."""
        claims = self.verify_token(token)
        if not claims or not claims.get("jti"):
            return False
        jti = claims["jti"]
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("INSERT INTO revoked_tokens (token_jti, revoked_at) VALUES (%s, %s) ON CONFLICT (token_jti) DO NOTHING;", (jti, now))
            conn.commit()
        return True

    def _is_token_revoked(self, jti: str) -> bool:
        with self._connection() as conn:
            row = conn.execute("SELECT token_jti FROM revoked_tokens WHERE token_jti = %s;", (jti,)).fetchone()
            return row is not None

    # =========================================================================
    # User Account Operations
    # =========================================================================

    def register_user(
        self,
        email: str,
        password: str,
        full_name: str,
        role: str = "farmer",
        phone: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Creates a new user account. Role must be 'farmer', 'admin', or 'owner'.
        Returns (success, message, user_dict).
        """
        clean_email = email.strip().lower()
        if not clean_email or "@" not in clean_email:
            return False, "Invalid email address format.", None
        if len(password) < 6:
            return False, "Password must be at least 6 characters.", None
        if role not in ("farmer", "admin", "owner"):
            return False, "Invalid role. Allowed roles are 'farmer', 'admin', or 'owner'.", None

        user_id = f"USER-{uuid.uuid4().hex[:8].upper()}"
        salt = uuid.uuid4().hex
        pw_hash = self._hash_password(password, salt)
        now = datetime.now(timezone.utc).isoformat()

        try:
            with self._connection() as conn:
                conn.execute("""
                    INSERT INTO users (user_id, email, full_name, password_hash, salt, role, phone, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                """, (user_id, clean_email, full_name.strip(), pw_hash, salt, role, phone or "", now, now))
                conn.commit()
            return True, "User created successfully.", {
                "user_id": user_id,
                "email": clean_email,
                "full_name": full_name.strip(),
                "role": role,
                "phone": phone or "",
                "created_at": now
            }
        except sqlite3.IntegrityError:
            return False, f"Account with email '{clean_email}' already exists.", None

    def authenticate_user(self, email: str, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Validates user credentials. Returns (success, message, user_profile).
        """
        clean_email = email.strip().lower()
        with self._connection() as conn:
            row = conn.execute("""
                SELECT user_id, email, full_name, password_hash, salt, role, phone, created_at, is_active
                FROM users WHERE email = %s;
            """, (clean_email,)).fetchone()

            if not row:
                return False, "Invalid email or password.", None

            if not row["is_active"]:
                return False, "User account is deactivated. Contact administrator.", None

            if not self._verify_password(password, row["salt"], row["password_hash"]):
                return False, "Invalid email or password.", None

            return True, "Authentication successful.", {
                "user_id": row["user_id"],
                "email": row["email"],
                "full_name": row["full_name"],
                "role": row["role"],
                "phone": row["phone"],
                "created_at": row["created_at"],
                "is_active": bool(row["is_active"]),
                "permissions": self.get_user_permissions(row["user_id"], row["role"])
            }

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with self._connection() as conn:
            row = conn.execute("""
                SELECT user_id, email, full_name, role, phone, created_at, is_active
                FROM users WHERE user_id = %s;
            """, (user_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_active"] = bool(d["is_active"])
            d["permissions"] = self.get_user_permissions(d["user_id"], d["role"])
            return d

    def list_users(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Admin operation: lists users."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT user_id, email, full_name, role, phone, created_at, is_active
                FROM users ORDER BY created_at DESC LIMIT %s;
            """, (limit,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d["is_active"])
                d["permissions"] = self.get_user_permissions(d["user_id"], d["role"])
                results.append(d)
            return results

    def set_user_active_status(self, user_id: str, is_active: bool) -> bool:
        """Admin operation: activate or deactivate user account (legacy method)."""
        with self._connection() as conn:
            cur = conn.execute("UPDATE users SET is_active = %s, updated_at = %s WHERE user_id = %s;", (1 if is_active else 0, datetime.now(timezone.utc).isoformat(), user_id))
            conn.commit()
            return cur.rowcount > 0

    def delete_user(self, user_id: str) -> bool:
        """Deletes user account and associated private data."""
        target = self.get_user_by_id(user_id)
        if not target or target["role"] == "owner":
            return False
        with self._connection() as conn:
            conn.execute("DELETE FROM sub_owner_permissions WHERE user_id = %s;", (user_id,))
            cur = conn.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
            conn.commit()
            return cur.rowcount > 0

    # =========================================================================
    # Owner & Administrator Governance System
    # =========================================================================

    def bootstrap_owner(
        self,
        email: str,
        password: str,
        full_name: str,
        phone: Optional[str] = None
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        One-time controlled bootstrap for project owner account.
        Permanently locked once an owner already exists in the database.
        """
        with self._connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'owner';").fetchone()
            if row and row["count"] > 0:
                return False, "Project owner already initialized. Bootstrap is permanently locked.", None

        # Check if email is already registered as a farmer/admin
        with self._connection() as conn:
            existing = conn.execute("SELECT user_id, email, full_name FROM users WHERE email = %s;", (email.strip().lower(),)).fetchone()
            if existing:
                now = datetime.now(timezone.utc).isoformat()
                conn.execute("UPDATE users SET role = 'owner', updated_at = %s WHERE user_id = %s;", (now, existing["user_id"]))
                conn.commit()
                self.log_audit_event(
                    actor_id=existing["user_id"],
                    actor_email=existing["email"],
                    actor_role="owner",
                    action="OWNER_BOOTSTRAP",
                    details=f"Promoted existing account {existing['email']} to Project Owner.",
                    target_user_id=existing["user_id"]
                )
                return True, "Existing account promoted to Project Owner.", {
                    "user_id": existing["user_id"],
                    "email": existing["email"],
                    "full_name": existing["full_name"],
                    "role": "owner"
                }

        # Create fresh owner account
        ok, msg, user = self.register_user(
            email=email,
            password=password,
            full_name=full_name,
            role="owner",
            phone=phone
        )
        if ok and user:
            self.log_audit_event(
                actor_id=user["user_id"],
                actor_email=user["email"],
                actor_role="owner",
                action="OWNER_BOOTSTRAP",
                details=f"Bootstrapped Project Owner account for {user['email']}.",
                target_user_id=user["user_id"]
            )
        return ok, msg, user

    def update_user_role(
        self,
        acting_user: Dict[str, Any],
        target_user_id: str,
        new_role: str
    ) -> Tuple[bool, str]:
        """
        Owner/Admin operation: updates a user's role with strict governance.
        - Acting user must be 'owner' or 'admin'.
        - Only 'owner' can assign the 'owner' role.
        - Cannot demote the last remaining active owner or admin.
        """
        actor_role = acting_user.get("role", "")
        if actor_role not in ("owner", "admin"):
            return False, "Unauthorized: Only owners or administrators can change user roles."

        if new_role not in ("farmer", "admin", "owner", "sub_owner"):
            return False, f"Invalid role '{new_role}'. Must be 'farmer', 'admin', 'sub_owner', or 'owner'."

        if new_role in ("owner", "sub_owner") and actor_role != "owner":
            return False, "Unauthorized: Only the project owner can appoint owners or sub-owners."

        target = self.get_user_by_id(target_user_id)
        if not target:
            return False, f"Target user '{target_user_id}' does not exist."

        old_role = target["role"]
        if old_role == new_role:
            return True, f"User already has role '{new_role}'."

        # Safety: Prevent demoting the last owner or last administrative account
        with self._connection() as conn:
            if old_role == "owner":
                owner_count = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'owner' AND is_active = 1;").fetchone()["count"]
                if owner_count <= 1:
                    return False, "Forbidden: Cannot demote the last remaining active Project Owner."
            elif old_role == "admin":
                admin_count = conn.execute("SELECT COUNT(*) as count FROM users WHERE role IN ('admin', 'owner') AND is_active = 1;").fetchone()["count"]
                if admin_count <= 1:
                    return False, "Forbidden: Cannot demote the last remaining administrative account."

            now = datetime.now(timezone.utc).isoformat()
            conn.execute("UPDATE users SET role = %s, updated_at = %s WHERE user_id = %s;", (new_role, now, target_user_id))
            if old_role == "sub_owner" and new_role != "sub_owner":
                conn.execute("DELETE FROM sub_owner_permissions WHERE user_id = %s;", (target_user_id,))
            conn.commit()

        self.log_audit_event(
            actor_id=acting_user.get("user_id", acting_user.get("sub", "UNKNOWN")),
            actor_email=acting_user.get("email", ""),
            actor_role=actor_role,
            action="ROLE_CHANGE",
            details=f"Changed role of user {target['email']} from '{old_role}' to '{new_role}'.",
            target_user_id=target_user_id
        )
        return True, f"User role updated to '{new_role}'."

    def set_user_status(
        self,
        acting_user: Dict[str, Any],
        target_user_id: str,
        is_active: bool
    ) -> Tuple[bool, str]:
        """
        Owner/Admin/Authorized Sub-Owner operation: activate or suspend a user account.
        Prevents deactivating oneself or the last owner.
        """
        actor_role = acting_user.get("role", "")
        actor_id = acting_user.get("user_id", acting_user.get("sub", ""))
        is_sub_owner_with_user_mgmt = (actor_role == "sub_owner" and self.has_permission(acting_user, "can_manage_users"))
        if actor_role not in ("owner", "admin") and not is_sub_owner_with_user_mgmt:
            return False, "Unauthorized: Insufficient privileges to change account status."

        if not is_active and actor_id == target_user_id:
            return False, "Forbidden: Administrators cannot deactivate their own account."

        target = self.get_user_by_id(target_user_id)
        if not target:
            return False, f"Target user '{target_user_id}' does not exist."

        if actor_role == "sub_owner" and target["role"] in ("owner", "admin", "sub_owner"):
            return False, "Forbidden: Sub-Owners cannot modify administrator, owner, or sub-owner accounts."

        if not is_active and target["role"] == "owner":
            with self._connection() as conn:
                owner_count = conn.execute("SELECT COUNT(*) as count FROM users WHERE role = 'owner' AND is_active = 1;").fetchone()["count"]
                if owner_count <= 1:
                    return False, "Forbidden: Cannot deactivate the last remaining Project Owner."

        with self._connection() as conn:
            now = datetime.now(timezone.utc).isoformat()
            conn.execute("UPDATE users SET is_active = %s, updated_at = %s WHERE user_id = %s;", (1 if is_active else 0, now, target_user_id))
            conn.commit()

        status_str = "ACTIVE" if is_active else "SUSPENDED"
        self.log_audit_event(
            actor_id=actor_id,
            actor_email=acting_user.get("email", ""),
            actor_role=actor_role,
            action="STATUS_CHANGE",
            details=f"Changed status of user {target['email']} to {status_str}.",
            target_user_id=target_user_id
        )
        return True, f"User account status changed to {status_str}."

    def search_users(
        self,
        query: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search users by name, email, or role filter."""
        with self._connection() as conn:
            sql = "SELECT user_id, email, full_name, role, phone, created_at, is_active FROM users WHERE 1=1"
            params: List[Any] = []
            if query and query.strip():
                clean_q = f"%{query.strip().lower()}%"
                sql += " AND (LOWER(email) LIKE ? OR LOWER(full_name) LIKE ?)"
                params.extend([clean_q, clean_q])
            if role and role.strip():
                sql += " AND role = ?"
                params.append(role.strip().lower())
            sql += " ORDER BY created_at DESC LIMIT ?;"
            params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["is_active"] = bool(d["is_active"])
                d["permissions"] = self.get_user_permissions(d["user_id"], d["role"])
                results.append(d)
            return results

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves immutable security audit logs."""
        with self._connection() as conn:
            rows = conn.execute("""
                SELECT log_id, actor_id, actor_email, actor_role, target_user_id, action, details, timestamp
                FROM audit_logs ORDER BY timestamp DESC LIMIT %s;
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def get_system_stats(self) -> Dict[str, Any]:
        """Retrieves system counts for admin dashboard."""
        with self._connection() as conn:
            total_users = conn.execute("SELECT COUNT(*) AS count FROM users;").fetchone()["count"]
            total_farmers = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'farmer';").fetchone()["count"]
            total_admins = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role IN ('admin', 'owner');").fetchone()["count"]
            total_sub_owners = conn.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'sub_owner';").fetchone()["count"]
            active_users = conn.execute("SELECT COUNT(*) AS count FROM users WHERE is_active = 1;").fetchone()["count"]
            suspended_users = conn.execute("SELECT COUNT(*) AS count FROM users WHERE is_active = 0;").fetchone()["count"]
            total_audits = conn.execute("SELECT COUNT(*) AS count FROM audit_logs;").fetchone()["count"]

        return {
            "total_users": total_users,
            "total_farmers": total_farmers,
            "total_admins": total_admins,
            "total_sub_owners": total_sub_owners,
            "active_users": active_users,
            "suspended_users": suspended_users,
            "total_audit_events": total_audits
        }

    # =========================================================================
    # Sub-Owner Governance (Main Project Owner Exclusively)
    # =========================================================================

    VALID_SUB_OWNER_PERMISSIONS = [
        "can_manage_users",
        "can_moderate_cases",
        "can_view_telemetry",
        "can_view_audit_logs"
    ]

    def get_sub_owner_permissions(self, user_id: str) -> List[str]:
        """Returns the list of administrative permissions assigned to a Sub-Owner."""
        with self._connection() as conn:
            row = conn.execute("SELECT permissions_json FROM sub_owner_permissions WHERE user_id = %s;", (user_id,)).fetchone()
            if row and row["permissions_json"]:
                try:
                    return json.loads(row["permissions_json"])
                except Exception:
                    return []
        return []

    def get_user_permissions(self, user_id: str, role: str) -> List[str]:
        """Returns effective permissions for a user based on role and explicit grants."""
        if role in ("owner", "admin"):
            return list(self.VALID_SUB_OWNER_PERMISSIONS)
        elif role == "sub_owner":
            return self.get_sub_owner_permissions(user_id)
        return []

    def list_sub_owners(self) -> List[Dict[str, Any]]:
        """Lists all Sub-Owners with their assigned permissions and metadata."""
        with self._connection() as conn:
            users = conn.execute("""
                SELECT u.user_id, u.email, u.full_name, u.role, u.is_active, u.created_at,
                       sp.permissions_json, sp.granted_by, sp.updated_at
                FROM users u
                LEFT JOIN sub_owner_permissions sp ON u.user_id = sp.user_id
                WHERE u.role = 'sub_owner'
                ORDER BY u.created_at DESC;
            """).fetchall()
            results = []
            for u in users:
                perms = []
                if u["permissions_json"]:
                    try:
                        perms = json.loads(u["permissions_json"])
                    except Exception:
                        pass
                results.append({
                    "user_id": u["user_id"],
                    "email": u["email"],
                    "full_name": u["full_name"],
                    "role": "sub_owner",
                    "is_active": bool(u["is_active"]),
                    "permissions": perms,
                    "granted_by": u["granted_by"] or "Main Owner",
                    "created_at": u["created_at"],
                    "updated_at": u["updated_at"] or u["created_at"]
                })
            return results

    def grant_sub_owner(
        self,
        acting_user: Dict[str, Any],
        target_user_id: str,
        permissions: List[str]
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Grants 'sub_owner' role with explicit configurable permissions.
        Strictly restricted to the Main Project Owner (role: 'owner').
        """
        actor_role = acting_user.get("role", "")
        actor_email = acting_user.get("email", "")
        actor_id = acting_user.get("user_id", acting_user.get("sub", "UNKNOWN"))

        if actor_role != "owner":
            return False, "Unauthorized: Only the Main Project Owner can grant Sub-Owner privileges.", None

        target = self.get_user_by_id(target_user_id)
        if not target:
            return False, f"Target user '{target_user_id}' does not exist.", None

        if target["role"] == "owner":
            return False, "Forbidden: The Main Project Owner account cannot be converted to Sub-Owner.", None

        # Filter to allowed permissions
        valid_perms = [p for p in permissions if p in self.VALID_SUB_OWNER_PERMISSIONS]
        if not valid_perms:
            valid_perms = ["can_view_telemetry"]

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("UPDATE users SET role = 'sub_owner', updated_at = %s WHERE user_id = %s;", (now, target_user_id))
            conn.execute("""
                INSERT INTO sub_owner_permissions (user_id, permissions_json, granted_by, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE SET
                    permissions_json = EXCLUDED.permissions_json,
                    granted_by = EXCLUDED.granted_by,
                    updated_at = EXCLUDED.updated_at;
            """, (target_user_id, json.dumps(valid_perms), actor_email, now, now))
            conn.commit()

        self.log_audit_event(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role="owner",
            action="SUB_OWNER_GRANTED",
            details=f"Main Owner granted Sub-Owner role to {target['email']} with permissions: {valid_perms}.",
            target_user_id=target_user_id
        )

        return True, f"Sub-Owner role successfully granted to {target['full_name']}.", {
            "user_id": target["user_id"],
            "email": target["email"],
            "full_name": target["full_name"],
            "role": "sub_owner",
            "is_active": bool(target["is_active"]),
            "permissions": valid_perms,
            "granted_by": actor_email,
            "updated_at": now
        }

    def revoke_sub_owner(
        self,
        acting_user: Dict[str, Any],
        target_user_id: str
    ) -> Tuple[bool, str]:
        """
        Immediately revokes Sub-Owner privileges and restores role to 'farmer'.
        Strictly restricted to the Main Project Owner.
        """
        actor_role = acting_user.get("role", "")
        actor_email = acting_user.get("email", "")
        actor_id = acting_user.get("user_id", acting_user.get("sub", "UNKNOWN"))

        if actor_role != "owner":
            return False, "Unauthorized: Only the Main Project Owner can revoke Sub-Owner privileges."

        target = self.get_user_by_id(target_user_id)
        if not target:
            return False, f"Target user '{target_user_id}' does not exist."

        if target["role"] == "owner":
            return False, "Forbidden: The Main Project Owner account cannot be revoked."

        if target["role"] != "sub_owner":
            return False, f"User {target['email']} is not a Sub-Owner (current role: {target['role']})."

        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("UPDATE users SET role = 'farmer', updated_at = %s WHERE user_id = %s;", (now, target_user_id))
            conn.execute("DELETE FROM sub_owner_permissions WHERE user_id = %s;", (target_user_id,))
            conn.commit()

        self.log_audit_event(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role="owner",
            action="SUB_OWNER_REVOKED",
            details=f"Main Owner revoked Sub-Owner privileges from {target['email']}. Role restored to 'farmer'.",
            target_user_id=target_user_id
        )

        return True, f"Sub-Owner privileges revoked from {target['email']}. Role restored to 'farmer'."

    def update_sub_owner_permissions(
        self,
        acting_user: Dict[str, Any],
        target_user_id: str,
        permissions: List[str]
    ) -> Tuple[bool, str, Optional[List[str]]]:
        """Updates permissions assigned to an existing Sub-Owner."""
        actor_role = acting_user.get("role", "")
        actor_email = acting_user.get("email", "")
        actor_id = acting_user.get("user_id", acting_user.get("sub", "UNKNOWN"))

        if actor_role != "owner":
            return False, "Unauthorized: Only the Main Project Owner can modify Sub-Owner permissions.", None

        target = self.get_user_by_id(target_user_id)
        if not target or target["role"] != "sub_owner":
            return False, f"Target user '{target_user_id}' is not an active Sub-Owner.", None

        valid_perms = [p for p in permissions if p in self.VALID_SUB_OWNER_PERMISSIONS]
        now = datetime.now(timezone.utc).isoformat()
        with self._connection() as conn:
            conn.execute("""
                UPDATE sub_owner_permissions SET permissions_json = %s, updated_at = %s WHERE user_id = %s;
            """, (json.dumps(valid_perms), now, target_user_id))
            conn.commit()

        self.log_audit_event(
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role="owner",
            action="SUB_OWNER_PERMISSIONS_UPDATED",
            details=f"Main Owner updated Sub-Owner permissions for {target['email']} to: {valid_perms}.",
            target_user_id=target_user_id
        )

        return True, "Sub-Owner permissions successfully updated.", valid_perms

    def has_permission(self, user_dict: Dict[str, Any], required_permission: str) -> bool:
        """
        Evaluates whether the user possesses the required permission.
        - 'owner' possesses ALL permissions without exception.
        - 'admin' possesses standard administrative permissions.
        - 'sub_owner' possesses only explicitly assigned permissions checked against the live database.
        - 'farmer' possesses no administrative permissions.
        """
        role = user_dict.get("role", "")
        if role == "owner":
            return True
        if role == "admin":
            return True
        if role == "sub_owner":
            user_id = user_dict.get("user_id") or user_dict.get("sub")
            if not user_id:
                return False
            perms = self.get_sub_owner_permissions(user_id)
            return required_permission in perms
        return False


# Global singleton
_AUTH_SERVICE: Optional[AuthService] = None


def get_auth_service(db_path: str = DEFAULT_DB_PATH) -> AuthService:
    global _AUTH_SERVICE
    if _AUTH_SERVICE is None:
        _AUTH_SERVICE = AuthService(db_path=db_path)
    return _AUTH_SERVICE


def set_auth_service(service: Optional[AuthService]) -> None:
    global _AUTH_SERVICE
    _AUTH_SERVICE = service
