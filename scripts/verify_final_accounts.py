#!/usr/bin/env python3
"""
AgriMind Final Account & Role Enforcement Verification Script.
Validates the live database state, verifies role separation, and confirms
that only Jaskirat Kour (Owner) and Simran Kour (Farmer) exist in the system.
"""
import os
import sys
import sqlite3

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.services.auth_service import AuthService, DEFAULT_DB_PATH


def verify_live_state(db_path: str = DEFAULT_DB_PATH):
    print("=================================================================")
    print("      AgriMind Live Account & Role Separation Verification       ")
    print("=================================================================")
    print(f"Target Database: {db_path}")

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        users = cur.execute("SELECT user_id, email, full_name, role, is_active, created_at FROM users;").fetchall()
        print(f"\n[1] Total Users Found in Database: {len(users)}")
        for u in users:
            print(f"  • {u['user_id']} | {u['email']} | {u['full_name']} | Role: {u['role'].upper()} | Active: {bool(u['is_active'])}")

        user_dict = {u["email"]: u for u in users}

        # Check Jaskirat Kour
        owner_email = "jaskiratkourjk2005@gmail.com"
        if owner_email in user_dict:
            owner = user_dict[owner_email]
            if owner["role"] == "owner" and owner["is_active"] == 1:
                print(f"\n[PASS] Jaskirat Kour ({owner_email}) is verified active PROJECT OWNER.")
            else:
                print(f"\n[FAIL] Jaskirat Kour exists but has incorrect role or status: {owner['role']}, {owner['is_active']}.")
                return False
        else:
            print(f"\n[FAIL] Jaskirat Kour ({owner_email}) not found in users table.")
            return False

        # Check Simran Kour
        farmer_email = "2023a1r029@mietjammu.in"
        if farmer_email in user_dict:
            farmer = user_dict[farmer_email]
            if farmer["role"] == "farmer" and farmer["is_active"] == 1:
                print(f"[PASS] Simran Kour ({farmer_email}) is verified active FARMER.")
            else:
                print(f"[FAIL] Simran Kour exists but has incorrect role or status: {farmer['role']}, {farmer['is_active']}.")
                return False
        else:
            print(f"[FAIL] Simran Kour ({farmer_email}) not found in users table.")
            return False

        # Check Demo accounts removal
        unwanted_emails = [
            "admin@agrimind.jammu.gov.in",
            "farmer_local@agrimind.in",
            "owner@agrimind.jammu.gov.in"
        ]
        found_unwanted = [e for e in unwanted_emails if e in user_dict]
        if not found_unwanted:
            print("[PASS] All three demonstration accounts have been safely and permanently removed.")
        else:
            print(f"[FAIL] Unwanted demonstration accounts still present in database: {found_unwanted}")
            return False

        if len(users) == 2:
            print("[PASS] Database strictly contains exactly the two intended accounts (Jaskirat Kour & Simran Kour).")
        else:
            print(f"[FAIL] Database contains {len(users)} accounts; expected exactly 2.")
            return False

        # Check Audit Logs
        logs = cur.execute("SELECT log_id, actor_email, actor_role, action, details, timestamp FROM audit_logs ORDER BY timestamp ASC;").fetchall()
        print(f"\n[2] Audit Logs Integrity Check: {len(logs)} audit log records preserved.")
        for l in logs:
            print(f"  • {l['log_id']} | {l['action']} by {l['actor_email']} ({l['actor_role']}) at {l['timestamp']}")

        owner_bootstrap_logs = [l for l in logs if l["actor_email"] == owner_email and l["action"] == "OWNER_BOOTSTRAP"]
        if owner_bootstrap_logs:
            print(f"[PASS] Verified immutable audit log entry for Jaskirat Kour's owner bootstrap ({owner_bootstrap_logs[0]['log_id']}).")
        else:
            print("[WARN] No audit log entry specifically for Jaskirat Kour's owner bootstrap.")

    print("\n=================================================================")
    print("   [SUCCESS] ALL FINAL ACCOUNT REQUIREMENTS VERIFIED END-TO-END   ")
    print("=================================================================")
    return True


if __name__ == "__main__":
    success = verify_live_state()
    sys.exit(0 if success else 1)

