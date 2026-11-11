"""
AgriMind Sub-Owner Governance & Security Verification Suite
Tests the complete Sub-Owner lifecycle under Main Project Owner supremacy.
"""
import os
import sys
import unittest
import tempfile
import sqlite3

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from fastapi.testclient import TestClient
from src.api.app import app
from src.services.auth_service import AuthService, set_auth_service
from src.api.case_store import CaseStore, set_case_store


class TestSubOwnerGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "test_cases.db")
        cls.auth_svc = AuthService(db_path=cls.db_path)
        cls.case_store = CaseStore(db_path=cls.db_path)
        set_auth_service(cls.auth_svc)
        set_case_store(cls.case_store)
        cls.client = TestClient(app)

        # 1. Setup Main Owner: Jaskirat Kour
        cls.owner_email = "jaskiratkourjk2005@gmail.com"
        cls.owner_pwd = "SecureOwnerPassword2026!"
        ok, msg, owner_user = cls.auth_svc.register_user(
            email=cls.owner_email,
            password=cls.owner_pwd,
            full_name="Jaskirat Kour",
            role="owner",
            phone="+91-9419100001"
        )
        assert ok, f"Failed to register owner: {msg}"
        cls.owner_id = owner_user["user_id"]
        cls.owner_token = cls.auth_svc.create_token(cls.owner_id, cls.owner_email, "owner")
        cls.owner_headers = {"Authorization": f"Bearer {cls.owner_token}"}

        # 2. Setup Farmer: Simran Kour
        cls.simran_email = "2023a1r029@mietjammu.in"
        cls.simran_pwd = "FarmerPassword2026!"
        ok, msg, simran_user = cls.auth_svc.register_user(
            email=cls.simran_email,
            password=cls.simran_pwd,
            full_name="Simran Kour",
            role="farmer",
            phone="+91-9419200002"
        )
        assert ok, f"Failed to register Simran: {msg}"
        cls.simran_id = simran_user["user_id"]
        cls.simran_token = cls.auth_svc.create_token(cls.simran_id, cls.simran_email, "farmer")
        cls.simran_headers = {"Authorization": f"Bearer {cls.simran_token}"}

        # 3. Setup Candidate User for Sub-Owner testing
        cls.candidate_email = "deputy_agronomist@agrimind.jammu.in"
        cls.candidate_pwd = "DeputyPassword2026!"
        ok, msg, candidate_user = cls.auth_svc.register_user(
            email=cls.candidate_email,
            password=cls.candidate_pwd,
            full_name="Deputy Agronomist",
            role="farmer"
        )
        assert ok, f"Failed to register candidate: {msg}"
        cls.candidate_id = candidate_user["user_id"]

    @classmethod
    def tearDownClass(cls):
        set_auth_service(None)
        set_case_store(None)
        cls.temp_dir.cleanup()

    def test_01_farmer_cannot_access_admin_or_sub_owner_routes(self):
        """Standard farmer token receives 403 Forbidden across all admin & governance endpoints."""
        res_sub = self.client.get("/admin/sub-owners", headers=self.simran_headers)
        self.assertEqual(res_sub.status_code, 403)

        res_users = self.client.get("/admin/users", headers=self.simran_headers)
        self.assertEqual(res_users.status_code, 403)

        res_telemetry = self.client.get("/admin/system/status", headers=self.simran_headers)
        self.assertEqual(res_telemetry.status_code, 403)

        res_audit = self.client.get("/admin/audit-logs", headers=self.simran_headers)
        self.assertEqual(res_audit.status_code, 403)

    def test_02_main_owner_grants_sub_owner_with_telemetry_only(self):
        """Main Project Owner grants 'sub_owner' role with restricted permission: 'can_view_telemetry'."""
        payload = {
            "user_id": self.candidate_id,
            "permissions": ["can_view_telemetry"]
        }
        res = self.client.post("/admin/sub-owners/grant", json=payload, headers=self.owner_headers)
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["sub_owner"]["role"], "sub_owner")
        self.assertIn("can_view_telemetry", data["sub_owner"]["permissions"])

        # Check DB role directly
        user_record = self.auth_svc.get_user_by_id(self.candidate_id)
        self.assertEqual(user_record["role"], "sub_owner")
        self.assertEqual(user_record["permissions"], ["can_view_telemetry"])

    def test_03_sub_owner_can_access_telemetry_but_denied_other_permissions(self):
        """Sub-Owner with telemetry permission can view telemetry, but cannot view users or audit logs."""
        cand_token = self.auth_svc.create_token(self.candidate_id, self.candidate_email, "sub_owner")
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Telemetry allowed
        res_telemetry = self.client.get("/admin/system/status", headers=cand_headers)
        self.assertEqual(res_telemetry.status_code, 200)
        self.assertEqual(res_telemetry.json()["system_stats"]["total_sub_owners"], 1)

        # 2. User management denied
        res_users = self.client.get("/admin/users", headers=cand_headers)
        self.assertEqual(res_users.status_code, 403)
        self.assertIn("can_manage_users", res_users.text)

        # 3. Audit logs denied
        res_audit = self.client.get("/admin/audit-logs", headers=cand_headers)
        self.assertEqual(res_audit.status_code, 403)
        self.assertIn("can_view_audit_logs", res_audit.text)

        # 4. Case moderation denied
        res_mod = self.client.delete("/admin/cases/CASE-NONEXISTENT", headers=cand_headers)
        self.assertEqual(res_mod.status_code, 403)
        self.assertIn("can_moderate_cases", res_mod.text)

    def test_04_sub_owner_supremacy_isolation(self):
        """Sub-Owner CANNOT manage sub-owners, modify roles, or deactivate Main Owner."""
        cand_token = self.auth_svc.create_token(self.candidate_id, self.candidate_email, "sub_owner")
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # 1. Cannot list sub-owners (Owner only)
        res_sub_list = self.client.get("/admin/sub-owners", headers=cand_headers)
        self.assertEqual(res_sub_list.status_code, 403)

        # 2. Cannot grant sub-owner privileges (Owner only)
        res_grant = self.client.post("/admin/sub-owners/grant", json={
            "user_id": self.simran_id,
            "permissions": ["can_view_telemetry"]
        }, headers=cand_headers)
        self.assertEqual(res_grant.status_code, 403)

        # 3. Cannot update user roles (Owner only)
        res_role = self.client.post(f"/admin/users/{self.candidate_id}/role", json={
            "role": "owner"
        }, headers=cand_headers)
        self.assertEqual(res_role.status_code, 403)

        # 4. Cannot deactivate Main Owner
        res_deactivate_owner = self.client.post(f"/admin/users/{self.owner_id}/status", json={
            "is_active": False
        }, headers=cand_headers)
        # 403 forbidden because sub-owner cannot touch owner
        self.assertIn(res_deactivate_owner.status_code, (400, 403))

    def test_05_main_owner_updates_sub_owner_permissions(self):
        """Main Project Owner expands Sub-Owner permissions to include user management."""
        new_perms = ["can_view_telemetry", "can_manage_users"]
        res = self.client.post(f"/admin/sub-owners/{self.candidate_id}/permissions", json={
            "permissions": new_perms
        }, headers=self.owner_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "success")

        # Now test that Sub-Owner can access user management
        cand_token = self.auth_svc.create_token(self.candidate_id, self.candidate_email, "sub_owner")
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        res_users = self.client.get("/admin/users", headers=cand_headers)
        self.assertEqual(res_users.status_code, 200)
        user_emails = [u["email"] for u in res_users.json()]
        self.assertIn(self.owner_email, user_emails)
        self.assertIn(self.simran_email, user_emails)

        # But still denied audit logs
        res_audit = self.client.get("/admin/audit-logs", headers=cand_headers)
        self.assertEqual(res_audit.status_code, 403)

    def test_06_immediate_revocation_and_token_invalidation(self):
        """Revoking Sub-Owner role immediately demotes user to farmer and invalidates administrative token access."""
        # Create an active token for the candidate while still sub_owner
        cand_token = self.auth_svc.create_token(self.candidate_id, self.candidate_email, "sub_owner")
        cand_headers = {"Authorization": f"Bearer {cand_token}"}

        # Verify it works prior to revocation
        pre_res = self.client.get("/admin/system/status", headers=cand_headers)
        self.assertEqual(pre_res.status_code, 200)

        # Main Owner revokes Sub-Owner privileges
        revoke_res = self.client.post(f"/admin/sub-owners/{self.candidate_id}/revoke", headers=self.owner_headers)
        self.assertEqual(revoke_res.status_code, 200)
        self.assertEqual(revoke_res.json()["status"], "success")

        # Verify DB state: role restored to farmer, permissions cleared
        revoked_user = self.auth_svc.get_user_by_id(self.candidate_id)
        self.assertEqual(revoked_user["role"], "farmer")
        self.assertEqual(revoked_user["permissions"], [])

        # Sub-owner permissions table entry must be deleted
        perms = self.auth_svc.get_sub_owner_permissions(self.candidate_id)
        self.assertEqual(perms, [])

        # IMMEDIATELY: Next request with the existing token is rejected with 403 Forbidden
        post_res = self.client.get("/admin/system/status", headers=cand_headers)
        self.assertEqual(post_res.status_code, 403)

        post_users = self.client.get("/admin/users", headers=cand_headers)
        self.assertEqual(post_users.status_code, 403)

    def test_07_audit_trail_recorded(self):
        """Verifies immutable audit trail logs SUB_OWNER_GRANTED, SUB_OWNER_PERMISSIONS_UPDATED, SUB_OWNER_REVOKED."""
        logs = self.auth_svc.get_audit_logs(limit=20)
        actions = [log["action"] for log in logs]
        self.assertIn("SUB_OWNER_GRANTED", actions)
        self.assertIn("SUB_OWNER_PERMISSIONS_UPDATED", actions)
        self.assertIn("SUB_OWNER_REVOKED", actions)

    def test_08_simran_kour_farmer_account_intact(self):
        """Verifies Simran Kour remains active farmer without any privilege alterations."""
        simran = self.auth_svc.get_user_by_id(self.simran_id)
        self.assertIsNotNone(simran)
        self.assertEqual(simran["email"], "2023a1r029@mietjammu.in")
        self.assertEqual(simran["role"], "farmer")
        self.assertTrue(simran["is_active"])


if __name__ == "__main__":
    unittest.main()
