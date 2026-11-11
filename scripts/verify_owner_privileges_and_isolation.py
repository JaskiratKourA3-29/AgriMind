#!/usr/bin/env python3
"""
Comprehensive Live Verification of Owner Privileges and Role Isolation.
Validates:
1. Jaskirat Kour (jaskiratkourjk2005@gmail.com, USER-3FC32032) is verified as Project Owner.
2. Owner has full administrative access to:
   - GET /admin/system/status
   - GET /admin/users
   - GET /admin/users/search
   - GET /admin/audit-logs
   - POST /admin/users/{user_id}/status
   - POST /admin/users/{user_id}/role (Owner-only endpoint)
3. Simran Kour (2023a1r029@mietjammu.in, USER-F6D3D213) is verified as Farmer.
4. Farmer token receives HTTP 403 Forbidden on all administrative endpoints.
5. Farmer token cannot update user roles or view audit logs.
6. Tokens for deleted demo accounts receive HTTP 401 Unauthorized.
7. Last-owner demotion protection is strictly enforced.
"""
import os
import sys
import unittest
from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.services.auth_service import AuthService, DEFAULT_DB_PATH


class TestLiveOwnerPrivileges(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.auth_svc = AuthService(db_path=DEFAULT_DB_PATH)
        cls.client = TestClient(app)

        # Retrieve live records directly from production DB
        cls.owner = cls.auth_svc.get_user_by_id("USER-3FC32032")
        cls.farmer = cls.auth_svc.get_user_by_id("USER-F6D3D213")

        assert cls.owner is not None, "Jaskirat Kour owner record not found in data/cases.db!"
        assert cls.farmer is not None, "Simran Kour farmer record not found in data/cases.db!"

        cls.owner_token = cls.auth_svc.create_token(
            cls.owner["user_id"], cls.owner["email"], cls.owner["role"]
        )
        cls.farmer_token = cls.auth_svc.create_token(
            cls.farmer["user_id"], cls.farmer["email"], cls.farmer["role"]
        )

    def test_01_database_account_integrity(self):
        """Verifies live database holds strictly the two authorized accounts."""
        users = self.auth_svc.list_users(limit=10)
        self.assertEqual(len(users), 2, "Database must contain exactly 2 accounts")

        emails = {u["email"]: u for u in users}
        self.assertIn("jaskiratkourjk2005@gmail.com", emails)
        self.assertIn("2023a1r029@mietjammu.in", emails)

        # Verify Jaskirat Kour
        owner = emails["jaskiratkourjk2005@gmail.com"]
        self.assertEqual(owner["role"], "owner", "Jaskirat Kour must possess 'owner' role")
        self.assertEqual(owner["user_id"], "USER-3FC32032")
        self.assertEqual(owner["full_name"], "Jaskirat Kour")
        self.assertTrue(owner["is_active"])

        # Verify Simran Kour
        farmer = emails["2023a1r029@mietjammu.in"]
        self.assertEqual(farmer["role"], "farmer", "Simran Kour must possess 'farmer' role")
        self.assertEqual(farmer["user_id"], "USER-F6D3D213")
        self.assertEqual(farmer["full_name"], "simran kour")
        self.assertTrue(farmer["is_active"])

        # Verify Demo accounts are gone
        self.assertNotIn("admin@agrimind.jammu.gov.in", emails)
        self.assertNotIn("farmer_local@agrimind.in", emails)
        self.assertNotIn("owner@agrimind.jammu.gov.in", emails)

    def test_02_owner_telemetry_access(self):
        """Verifies owner can access /admin/system/status telemetry."""
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = self.client.get("/admin/system/status", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_users", data)
        self.assertEqual(data["total_users"], 2)
        self.assertEqual(data["vectorstore_chunks"], 63)
        self.assertEqual(data["vision_model_status"], "active")

    def test_03_owner_user_management_access(self):
        """Verifies owner can access user list and search users."""
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = self.client.get("/admin/users", headers=headers)
        self.assertEqual(res.status_code, 200)
        users = res.json()
        self.assertEqual(len(users), 2)

        res_search = self.client.get("/admin/users/search?query=simran", headers=headers)
        self.assertEqual(res_search.status_code, 200)
        results = res_search.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["email"], "2023a1r029@mietjammu.in")

    def test_04_owner_audit_logs_access(self):
        """Verifies owner can access immutable security audit logs."""
        headers = {"Authorization": f"Bearer {self.owner_token}"}
        res = self.client.get("/admin/audit-logs", headers=headers)
        self.assertEqual(res.status_code, 200)
        logs = res.json()
        self.assertTrue(len(logs) >= 3)
        actions = [l["action"] for l in logs]
        self.assertIn("OWNER_BOOTSTRAP", actions)

    def test_05_farmer_forbidden_from_admin_endpoints(self):
        """Verifies farmer account (Simran Kour) is strictly denied administrative access."""
        headers = {"Authorization": f"Bearer {self.farmer_token}"}

        # Telemetry denied
        res_status = self.client.get("/admin/system/status", headers=headers)
        self.assertEqual(res_status.status_code, 403)
        self.assertIn("administrative privileges required", res_status.json()["detail"].lower())

        # User list denied
        res_users = self.client.get("/admin/users", headers=headers)
        self.assertEqual(res_users.status_code, 403)

        # User search denied
        res_search = self.client.get("/admin/users/search", headers=headers)
        self.assertEqual(res_search.status_code, 403)

        # Audit logs denied
        res_logs = self.client.get("/admin/audit-logs", headers=headers)
        self.assertEqual(res_logs.status_code, 403)

        # Role change denied
        res_role = self.client.post(
            f"/admin/users/{self.farmer['user_id']}/role",
            json={"role": "owner"},
            headers=headers
        )
        self.assertEqual(res_role.status_code, 403)

    def test_06_deleted_demo_accounts_tokens_rejected(self):
        """Verifies that tokens for deleted demo accounts are immediately rejected with HTTP 401."""
        # Simulated token for deleted demo admin
        dummy_admin_token = self.auth_svc.create_token("USER-66B7FD06", "admin@agrimind.jammu.gov.in", "admin")
        res = self.client.get("/admin/users", headers={"Authorization": f"Bearer {dummy_admin_token}"})
        self.assertEqual(res.status_code, 401)
        self.assertIn("does not exist", res.json()["detail"].lower())

        # Simulated token for deleted demo owner
        dummy_owner_token = self.auth_svc.create_token("USER-B6399749", "owner@agrimind.jammu.gov.in", "owner")
        res = self.client.get("/admin/system/status", headers={"Authorization": f"Bearer {dummy_owner_token}"})
        self.assertEqual(res.status_code, 401)

    def test_07_last_owner_protection(self):
        """Verifies that the sole remaining Project Owner cannot be demoted or deleted."""
        headers = {"Authorization": f"Bearer {self.owner_token}"}

        # Attempt to demote Jaskirat Kour to farmer -> rejected
        res = self.client.post(
            f"/admin/users/{self.owner['user_id']}/role",
            json={"role": "farmer"},
            headers=headers
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("cannot demote the last remaining active project owner", res.json()["detail"].lower())

        # Attempt to deactivate Jaskirat Kour -> rejected
        res_deactivate = self.client.post(
            f"/admin/users/{self.owner['user_id']}/status",
            json={"is_active": False},
            headers=headers
        )
        self.assertEqual(res_deactivate.status_code, 400)
        self.assertIn("cannot deactivate their own account", res_deactivate.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()
