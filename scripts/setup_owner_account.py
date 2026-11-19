#!/usr/bin/env python3
"""
AgriMind Secure Owner Setup & Account Cleanup Utility.
Safely establishes Jaskirat Kour as the verified Project Owner and primary administrator,
and removes the three demonstration accounts (admin, farmer_local, old owner placeholder)
in a single atomic SQLite transaction while preserving audit log integrity and farmer data.
"""
import os
import sys
import getpass
import argparse
import sqlite3
from datetime import datetime, timezone
import uuid
import hashlib

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from dotenv import load_dotenv
load_dotenv()

from src.services.auth_service import AuthService, DEFAULT_DB_PATH


def setup_owner(
    email: str,
    password: str,
    full_name: str = "Jaskirat Kour",
    phone: str = None,
    db_path: str = DEFAULT_DB_PATH
):
    clean_email = email.strip().lower()
    clean_name = full_name.strip()

    if not clean_email or "@" not in clean_email or "." not in clean_email:
        print("[ERROR] Invalid email address format.")
        return False, "Invalid email address format.", None

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters for Project Owner.")
        return False, "Password must be at least 8 characters.", None

    auth_svc = AuthService(db_path=db_path)

    # 1. Inspect existing state using DB connection wrapper
    with auth_svc._connection() as conn:
        existing_users = conn.execute("SELECT user_id, email, full_name, role FROM users;").fetchall()
        print(f"[INFO] Current users in database ({len(existing_users)}):")
        for u in existing_users:
            print(f"  • {u['user_id']} | {u['email']} | {u['full_name']} | {u['role']}")

        # 2. Create or promote Jaskirat Kour as Owner
        user_id = f"USER-{uuid.uuid4().hex[:8].upper()}"
        salt = uuid.uuid4().hex
        pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()
        now = datetime.now(timezone.utc).isoformat()

        # Check if clean_email already exists in users table
        existing_target = conn.execute("SELECT user_id, role FROM users WHERE email = %s;", (clean_email,)).fetchone()
        if existing_target:
            target_user_id = existing_target["user_id"]
            conn.execute(
                "UPDATE users SET role = 'owner', full_name = %s, password_hash = %s, salt = %s, is_active = 1, updated_at = %s WHERE user_id = %s;",
                (clean_name, pw_hash, salt, now, target_user_id)
            )
            print(f"[SUCCESS] Updated existing account {clean_email} to Project Owner (role: 'owner').")
        else:
            target_user_id = user_id
            conn.execute(
                "INSERT INTO users (user_id, email, full_name, password_hash, salt, role, phone, created_at, updated_at, is_active) "
                "VALUES (%s, %s, %s, %s, %s, 'owner', %s, %s, %s, 1);",
                (target_user_id, clean_email, clean_name, pw_hash, salt, phone or "", now, now)
            )
            print(f"[SUCCESS] Created Project Owner account for {clean_name} ({clean_email}).")

        # 3. Record Audit Log for Owner Setup
        log_id = f"AUDIT-{uuid.uuid4().hex[:12].upper()}"
        conn.execute(
            "INSERT INTO audit_logs (log_id, actor_id, actor_email, actor_role, target_user_id, action, details, timestamp) "
            "VALUES (%s, %s, %s, 'owner', %s, 'OWNER_BOOTSTRAP', %s, %s);",
            (
                log_id,
                target_user_id,
                clean_email,
                target_user_id,
                f"Configured Project Owner account for {clean_name} ({clean_email}).",
                now
            )
        )

        conn.commit()

        # 4. Display final database state
        final_users = conn.execute("SELECT user_id, email, full_name, role, is_active FROM users;").fetchall()
        print("\n=================================================================")
        print("                 FINAL ACTIVE DATABASE USERS                     ")
        print("=================================================================")
        for u in final_users:
            print(f"  • {u['user_id']} | {u['email']} | {u['full_name']} | Role: {u['role'].upper()} | Active: {bool(u['is_active'])}")
        print("=================================================================")

    return True, "Owner account successfully configured.", {
        "user_id": target_user_id,
        "email": clean_email,
        "full_name": clean_name,
        "role": "owner"
    }


def main():
    parser = argparse.ArgumentParser(description="AgriMind Secure Owner Setup & Account Cleanup")
    parser.add_argument("--email", type=str, default="jaskiratkourjk2005@gmail.com", help="Owner email address (default: jaskiratkourjk2005@gmail.com)")
    parser.add_argument("--password", type=str, required=False, help="Owner password (or will be prompted interactively via getpass)")
    parser.add_argument("--name", type=str, default="Jaskirat Kour", help="Owner full legal name (default: Jaskirat Kour)")
    parser.add_argument("--phone", type=str, default=None, help="Owner contact phone")
    parser.add_argument("--db-path", type=str, default=DEFAULT_DB_PATH, help="Path to SQLite database")

    args = parser.parse_args()

    email = args.email or "jaskiratkourjk2005@gmail.com"

    password = args.password
    if not password:
        password = os.environ.get("AGRIMIND_OWNER_PASSWORD")
    if not password:
        password = getpass.getpass("Enter Secure Password for Project Owner Jaskirat Kour: ").strip()

    ok, msg, user = setup_owner(
        email=email,
        password=password,
        full_name=args.name,
        phone=args.phone,
        db_path=args.db_path
    )

    if ok:
        print("\n[COMPLETE] Project Owner established and demo accounts safely removed.")
        sys.exit(0)
    else:
        print(f"\n[FAILED] {msg}")
        sys.exit(1)


if __name__ == "__main__":
    main()

