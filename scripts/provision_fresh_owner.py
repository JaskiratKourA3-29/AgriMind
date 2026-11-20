#!/usr/bin/env python3
"""
AgriMind Secure Fresh Owner Account Provisioning Script.

Requirements addressed:
1. Assigns the 'owner' role exclusively through a protected backend operation (direct database transaction with PBKDF2-HMAC-SHA256).
2. Generates a cryptographically secure random password (or accepts an explicit password).
3. Saves credentials strictly to a private, git-ignored local file (.credentials/owner_credentials.txt).
4. Never hardcodes credentials or prints secrets in logs, stdout, or reports.
5. Preserves all existing farmer accounts and their prediction data.
6. Verifies that the new account authenticates against production (https://agrimind-seven.vercel.app)
   and receives all four owner permissions:
   ['can_manage_users', 'can_moderate_cases', 'can_view_telemetry', 'can_view_audit_logs'].
7. Enforces database uniqueness and prevents duplicate accounts.
"""

import os
import sys
import json
import uuid
import secrets
import string
import hashlib
import argparse
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(WORKSPACE_DIR, ".env"))

try:
    import psycopg2
    import psycopg2.extras
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False


DEFAULT_EMAIL = "jaskiratkourjk2005@gmail.com"
DEFAULT_NAME = "Jaskirat Kour"
DEFAULT_PHONE = "+91-9876543210"
DEFAULT_CREDS_FILE = os.path.join(WORKSPACE_DIR, ".credentials", "owner_credentials.txt")
LIVE_BACKEND_URL = "https://agrimind-seven.vercel.app"
PBKDF2_ITERATIONS = 100_000
EXPECTED_PERMISSIONS = [
    "can_manage_users",
    "can_moderate_cases",
    "can_view_telemetry",
    "can_view_audit_logs"
]


def generate_secure_password(length: int = 20) -> str:
    """
    Generates a cryptographically strong random password meeting all complexity criteria.
    Contains uppercase, lowercase, numbers, and symbols.
    """
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        if (any(c.islower() for c in pwd)
                and any(c.isupper() for c in pwd)
                and any(c.isdigit() for c in pwd)
                and any(c in "!@#$%^&*" for c in pwd)):
            return pwd


def hash_password(password: str, salt: str) -> str:
    """Derives a PBKDF2-HMAC-SHA256 hex digest using 100,000 iterations."""
    derived = hashlib.pbkdf2_hmac(
        hash_name="sha256",
        password=password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        iterations=PBKDF2_ITERATIONS
    )
    return derived.hex()


def get_clean_pg_url(db_url: str) -> str:
    """Normalizes Neon connection string for Windows DNS compatibility."""
    if "-pooler" in db_url:
        parsed = urllib.parse.urlparse(db_url)
        netloc = parsed.netloc.replace("-pooler", "")
        return urllib.parse.urlunparse((parsed.scheme, netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
    return db_url


def provision_owner_account(
    email: str = DEFAULT_EMAIL,
    full_name: str = DEFAULT_NAME,
    phone: str = DEFAULT_PHONE,
    password: Optional[str] = None,
    creds_file: str = DEFAULT_CREDS_FILE,
    live_verify: bool = True
) -> Dict[str, Any]:
    """
    Executes fresh owner account provisioning with protected database transactions,
    verification of farmer accounts preservation, and live production authentication check.
    """
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    if not clean_email or "@" not in clean_email or "." not in clean_email:
        raise ValueError(f"Invalid email address: {email}")

    # 1. Prepare secure password
    generated = False
    if not password:
        password = generate_secure_password(20)
        generated = True

    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")

    salt = uuid.uuid4().hex
    pw_hash = hash_password(password, salt)
    user_id = f"USER-{uuid.uuid4().hex[:8].upper()}"
    now_iso = datetime.now(timezone.utc).isoformat()

    results: Dict[str, Any] = {
        "email": clean_email,
        "full_name": clean_name,
        "user_id": user_id,
        "role": "owner",
        "created_at": now_iso,
        "password_generated": generated,
        "password_length": len(password),
        "creds_file": creds_file,
        "neon_provisioned": False,
        "sqlite_provisioned": False,
        "farmers_preserved": 0,
        "live_authenticated": False,
        "permissions_verified": False,
        "permissions": []
    }

    # 2. Database Provisioning - Neon PostgreSQL (Production authoritative)
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL not found in environment (.env).")
    if not PSYCOPG2_AVAILABLE:
        raise RuntimeError("psycopg2 is not installed.")

    clean_url = get_clean_pg_url(db_url)
    conn_pg = psycopg2.connect(clean_url, sslmode="require")
    try:
        cur_pg = conn_pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # A. Check existing farmer accounts before provisioning
        cur_pg.execute("SELECT count(*) as count FROM users WHERE role = 'farmer';")
        farmer_cnt_before = cur_pg.fetchone()["count"]
        print(f"[PRE-CHECK] Existing farmer accounts in Neon PostgreSQL: {farmer_cnt_before}")

        # B. Check if target account already exists (prevent duplicate accounts)
        cur_pg.execute("SELECT user_id, email, role FROM users WHERE lower(email) = lower(%s);", (clean_email,))
        existing = cur_pg.fetchone()
        if existing:
            target_uid = existing["user_id"]
            print(f"[NOTICE] Account {clean_email} already exists with user_id={target_uid}. Updating to fresh owner.")
            cur_pg.execute("""
                UPDATE users
                SET full_name = %s,
                    password_hash = %s,
                    salt = %s,
                    role = 'owner',
                    phone = %s,
                    is_active = 1,
                    updated_at = %s
                WHERE user_id = %s;
            """, (clean_name, pw_hash, salt, phone or "", now_iso, target_uid))
            results["user_id"] = target_uid
        else:
            print(f"[ACTION] Inserting fresh owner record for {clean_email} ({user_id}).")
            cur_pg.execute("""
                INSERT INTO users (user_id, email, full_name, password_hash, salt, role, phone, created_at, updated_at, is_active)
                VALUES (%s, %s, %s, %s, %s, 'owner', %s, %s, %s, 1);
            """, (user_id, clean_email, clean_name, pw_hash, salt, phone or "", now_iso, now_iso))

        # C. Audit log entry
        audit_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
        cur_pg.execute("""
            INSERT INTO audit_logs (log_id, actor_id, actor_email, actor_role, target_user_id, action, details, timestamp)
            VALUES (%s, %s, %s, 'owner', %s, 'OWNER_PROVISIONING', %s, %s);
        """, (
            audit_id,
            results["user_id"],
            clean_email,
            results["user_id"],
            f"Provisioned fresh Project Owner account for {clean_name} ({clean_email}) via protected backend operation.",
            now_iso
        ))

        # D. Verify farmer accounts are preserved
        cur_pg.execute("SELECT count(*) as count FROM users WHERE role = 'farmer';")
        farmer_cnt_after = cur_pg.fetchone()["count"]
        if farmer_cnt_after != farmer_cnt_before:
            conn_pg.rollback()
            raise RuntimeError(f"Farmer accounts count changed! Before: {farmer_cnt_before}, After: {farmer_cnt_after}. Transaction aborted.")

        # E. Verify single owner account
        cur_pg.execute("SELECT count(*) as count FROM users WHERE lower(email) = lower(%s);", (clean_email,))
        owner_email_cnt = cur_pg.fetchone()["count"]
        if owner_email_cnt != 1:
            conn_pg.rollback()
            raise RuntimeError(f"Uniqueness violation: found {owner_email_cnt} accounts for {clean_email}!")

        conn_pg.commit()
        results["neon_provisioned"] = True
        results["farmers_preserved"] = farmer_cnt_after
        print(f"[SUCCESS] Neon PostgreSQL updated. Total farmers preserved: {farmer_cnt_after}.")
    finally:
        conn_pg.close()

    # 3. Database Mirroring - Local SQLite (data/cases.db) if present
    sqlite_path = os.path.join(WORKSPACE_DIR, "data", "cases.db")
    if os.path.exists(sqlite_path) and SQLITE_AVAILABLE:
        try:
            conn_sq = sqlite3.connect(sqlite_path)
            cur_sq = conn_sq.cursor()
            cur_sq.execute("SELECT user_id FROM users WHERE lower(email) = lower(?)", (clean_email,))
            sq_exist = cur_sq.fetchone()
            if sq_exist:
                cur_sq.execute("""
                    UPDATE users
                    SET full_name = ?, password_hash = ?, salt = ?, role = 'owner', phone = ?, is_active = 1, updated_at = ?
                    WHERE user_id = ?;
                """, (clean_name, pw_hash, salt, phone or "", now_iso, sq_exist[0]))
            else:
                cur_sq.execute("""
                    INSERT INTO users (user_id, email, full_name, password_hash, salt, role, phone, created_at, updated_at, is_active)
                    VALUES (?, ?, ?, ?, ?, 'owner', ?, ?, ?, 1);
                """, (results["user_id"], clean_email, clean_name, pw_hash, salt, phone or "", now_iso, now_iso))
            conn_sq.commit()
            conn_sq.close()
            results["sqlite_provisioned"] = True
            print(f"[SUCCESS] Local SQLite ({sqlite_path}) synchronized.")
        except Exception as e:
            print(f"[WARNING] Local SQLite mirror failed (non-critical): {e}")

    # 4. Save credentials to private git-ignored file
    os.makedirs(os.path.dirname(os.path.abspath(creds_file)), exist_ok=True)
    creds_content = (
        "=============================================================================\n"
        "AgriMind - Project Owner Production Authentication Credentials\n"
        "CONFIDENTIAL - DO NOT COMMIT TO GIT OR SHARE IN PUBLIC LOGS\n"
        "=============================================================================\n"
        f"Email:              {clean_email}\n"
        f"Full Name:          {clean_name}\n"
        f"Role:               owner\n"
        f"User ID:            {results['user_id']}\n"
        f"Phone:              {phone or 'N/A'}\n"
        f"Password:           {password}\n"
        f"Provisioned At:     {now_iso}\n"
        f"Production Gateway: {LIVE_BACKEND_URL}\n"
        "Permissions:\n"
        "  - can_manage_users\n"
        "  - can_moderate_cases\n"
        "  - can_view_telemetry\n"
        "  - can_view_audit_logs\n"
        "=============================================================================\n"
    )
    with open(creds_file, "w", encoding="utf-8") as f:
        f.write(creds_content)
    print(f"[SECURITY] Credentials written to local private file: {creds_file}")

    # 5. Live Production Authentication Verification
    if live_verify:
        print(f"\n[VERIFICATION] Probing live production gateway: {LIVE_BACKEND_URL}/auth/login")
        login_payload = json.dumps({"email": clean_email, "password": password}).encode("utf-8")
        req = urllib.request.Request(
            f"{LIVE_BACKEND_URL}/auth/login",
            data=login_payload,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "AgriMind-OwnerProvisioner/1.0"
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                status_code = resp.status
                body = json.loads(resp.read().decode("utf-8"))
                
                if status_code == 200 and "access_token" in body:
                    results["live_authenticated"] = True
                    user_info = body.get("user", {})
                    token = body.get("access_token")
                    actual_role = user_info.get("role")
                    actual_perms = user_info.get("permissions", [])
                    results["permissions"] = actual_perms
                    
                    print(f"  HTTP Status      : {status_code} OK")
                    print(f"  Authenticated User: {user_info.get('email')}")
                    print(f"  Assigned Role    : {actual_role}")
                    print(f"  Permissions Count: {len(actual_perms)}")
                    
                    # Verify role is owner
                    if actual_role != "owner":
                        raise RuntimeError(f"Expected role 'owner', got '{actual_role}'!")
                    
                    # Verify all 4 permissions
                    all_present = all(p in actual_perms for p in EXPECTED_PERMISSIONS)
                    if all_present and len(actual_perms) == 4:
                        results["permissions_verified"] = True
                        print(f"  Permissions OK   : All 4 Owner Permissions Verified: {actual_perms}")
                    else:
                        print(f"  Permissions MISMATCH: Expected {EXPECTED_PERMISSIONS}, got {actual_perms}")
                    
                    # Test /auth/me with Bearer token
                    req_me = urllib.request.Request(
                        f"{LIVE_BACKEND_URL}/auth/me",
                        headers={
                            "Authorization": f"Bearer {token}",
                            "User-Agent": "AgriMind-OwnerProvisioner/1.0"
                        },
                        method="GET"
                    )
                    with urllib.request.urlopen(req_me, timeout=30) as resp_me:
                        if resp_me.status == 200:
                            print(f"  /auth/me Endpoint: HTTP 200 OK (Bearer Session Validated)")
                else:
                    print(f"  Unexpected response body: {body}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            print(f"  [ERROR] Live authentication failed: HTTP {e.code} - {err_body}")
            raise
        except Exception as e:
            print(f"  [ERROR] Connection error during live verification: {e}")
            raise

    return results


def main():
    parser = argparse.ArgumentParser(description="AgriMind Secure Owner Account Provisioning CLI")
    parser.add_argument("--email", default=DEFAULT_EMAIL, help="Owner email address")
    parser.add_argument("--name", default=DEFAULT_NAME, help="Owner full name")
    parser.add_argument("--phone", default=DEFAULT_PHONE, help="Owner phone number")
    parser.add_argument("--password", default=None, help="Explicit password (if omitted, generates random 20-char password)")
    parser.add_argument("--creds-file", default=DEFAULT_CREDS_FILE, help="Path to save credentials securely")
    parser.add_argument("--no-verify", action="store_true", help="Skip live production verification")

    args = parser.parse_args()

    print("=" * 70)
    print("AGRIMIND SECURE OWNER ACCOUNT PROVISIONING")
    print("=" * 70)
    print(f"Target Email      : {args.email}")
    print(f"Target Name       : {args.name}")
    print(f"Credentials Output: {args.creds_file}")
    print("=" * 70)

    try:
        res = provision_owner_account(
            email=args.email,
            full_name=args.name,
            phone=args.phone,
            password=args.password,
            creds_file=args.creds_file,
            live_verify=not args.no_verify
        )
        print("\n" + "=" * 70)
        print("PROVISIONING COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print(f"User ID              : {res['user_id']}")
        print(f"Email                : {res['email']}")
        print(f"Role                 : {res['role']}")
        print(f"Neon PostgreSQL Sync : {'SUCCESS' if res['neon_provisioned'] else 'FAILED'}")
        print(f"Farmers Preserved    : {res['farmers_preserved']} accounts")
        print(f"Live Authentication  : {'SUCCESS (HTTP 200)' if res['live_authenticated'] else 'FAILED'}")
        print(f"Owner Permissions    : {'ALL 4 VERIFIED' if res['permissions_verified'] else 'FAILED'}")
        print(f"Local Secret File    : {res['creds_file']}")
        print("=" * 70)
        print("[IMPORTANT] The password has NOT been printed here for security.")
        print(f"[IMPORTANT] Read your credentials from: {res['creds_file']}")
        print("=" * 70)
    except Exception as e:
        print(f"\n[FATAL ERROR] Provisioning failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
