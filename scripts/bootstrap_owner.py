#!/usr/bin/env python3
"""
AgriMind Owner Bootstrap CLI Utility.
Provides a strictly controlled, one-time mechanism to establish the Project Owner account.
Once a project owner is initialized, this utility is permanently locked.
"""
import os
import sys
import argparse

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.services.auth_service import get_auth_service, DEFAULT_DB_PATH


def main():
    parser = argparse.ArgumentParser(
        description="AgriMind Project Owner One-Time Bootstrap Utility"
    )
    parser.add_argument(
        "--email",
        type=str,
        default="owner@agrimind.jammu.gov.in",
        help="Owner email address (default: owner@agrimind.jammu.gov.in)"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="AgriMindOwner#2026",
        help="Initial owner secure password (min 6 characters)"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="AgriMind Principal Investigator",
        help="Owner full legal name or title"
    )
    parser.add_argument(
        "--phone",
        type=str,
        default="+91-191-2470001",
        help="Official contact number"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database (default: data/cases.db)"
    )

    args = parser.parse_args()

    print("=================================================================")
    print("      AgriMind Project Owner One-Time Bootstrap Utility          ")
    print("=================================================================")
    print(f"Target Database : {args.db_path}")
    print(f"Owner Email     : {args.email}")
    print(f"Owner Name      : {args.name}")
    print(f"Contact Phone   : {args.phone}")
    print("-----------------------------------------------------------------")

    auth_svc = get_auth_service(db_path=args.db_path)

    ok, msg, user = auth_svc.bootstrap_owner(
        email=args.email,
        password=args.password,
        full_name=args.name,
        phone=args.phone
    )

    if ok:
        print("[SUCCESS] Project Owner Successfully Initialized!")
        print(f"  User ID : {user.get('user_id')}")
        print(f"  Email   : {user.get('email')}")
        print(f"  Role    : {user.get('role')}")
        print("  Status  : ACTIVE")
        print("-----------------------------------------------------------------")
        print("[SECURITY NOTICE] Bootstrap is now PERMANENTLY LOCKED.")
        print("Subsequent attempts to run this script will be rejected.")
        print("Keep owner credentials confidential and store in a secure vault.")
        print("=================================================================")
        sys.exit(0)
    else:
        print(f"[REJECTED] {msg}")
        print("=================================================================")
        sys.exit(1)


if __name__ == "__main__":
    main()

