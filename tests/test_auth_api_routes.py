"""
End-to-End API Integration Test Suite for Authentication & Role Enforcement (Stage C).
Verifies:
1. POST /auth/signup creates account and issues Bearer token.
2. POST /auth/login authenticates user and issues Bearer token.
3. GET /auth/me requires valid Bearer token (401 on missing/invalid).
4. POST /auth/logout revokes token immediately.
5. Farmer token attempting GET /admin/users returns HTTP 403 Forbidden.
6. Admin token attempting GET /admin/users returns HTTP 200 OK.
7. Admin token attempting GET /admin/system/status returns telemetry.
"""
import os
import sys
import tempfile
import unittest

from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.services.auth_service import AuthService, set_auth_service, get_auth_service


class TestAuthApiRoutes(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.auth_svc = AuthService(db_path=self.temp_db.name, secret_key="test-api-secret-key")
        set_auth_service(self.auth_svc)
        self.client = TestClient(app)

    def tearDown(self):
        set_auth_service(None)
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    def test_01_signup_and_me(self):
        """Verifies farmer signup and accessing /auth/me with Bearer token."""
        # Signup
        signup_payload = {
            "email": "farmer_ramesh@example.com",
            "password": "Password123",
            "full_name": "Ramesh Singh",
            "role": "farmer",
            "phone": "+919876543210"
        }
        res_signup = self.client.post("/auth/signup", json=signup_payload)
        self.assertEqual(res_signup.status_code, 201)
        data = res_signup.json()
        token = data["access_token"]
        self.assertEqual(data["user"]["email"], "farmer_ramesh@example.com")
        self.assertEqual(data["user"]["role"], "farmer")

        # Access /auth/me with token
        res_me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)
        self.assertEqual(res_me.json()["email"], "farmer_ramesh@example.com")

        # Access /auth/me without token -> 401
        res_no_auth = self.client.get("/auth/me")
        self.assertEqual(res_no_auth.status_code, 401)

        # Access /auth/me with garbage token -> 401
        res_bad_auth = self.client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.xyz"})
        self.assertEqual(res_bad_auth.status_code, 401)

    def test_02_login_and_logout_revocation(self):
        """Verifies login generates valid token and logout immediately invalidates it."""
        self.auth_svc.register_user("farmer_login@example.com", "Password123", "Login Farmer")

        # Successful login
        res_login = self.client.post("/auth/login", json={
            "email": "farmer_login@example.com",
            "password": "Password123"
        })
        self.assertEqual(res_login.status_code, 200)
        token = res_login.json()["access_token"]

        # Token works
        res_me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)

        # Logout
        res_logout = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_logout.status_code, 200)

        # Token is now revoked -> 401
        res_me_revoked = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me_revoked.status_code, 401)

    def test_03_role_enforcement_farmer_cannot_access_admin(self):
        """Verifies that farmers receive HTTP 403 when accessing administrative endpoints."""
        _, _, farmer = self.auth_svc.register_user("farmer_user@example.com", "Password123", "Farmer User", role="farmer")
        farmer_token = self.auth_svc.create_token(farmer["user_id"], farmer["email"], farmer["role"])

        # Farmer attempts to access /admin/users -> 403 Forbidden
        res_admin = self.client.get("/admin/users", headers={"Authorization": f"Bearer {farmer_token}"})
        self.assertEqual(res_admin.status_code, 403)
        self.assertIn("administrative privileges required", res_admin.json()["detail"].lower())

        # Farmer attempts to access /admin/system/status -> 403 Forbidden
        res_status = self.client.get("/admin/system/status", headers={"Authorization": f"Bearer {farmer_token}"})
        self.assertEqual(res_status.status_code, 403)

    def test_04_admin_can_access_admin_endpoints(self):
        """Verifies authorized administrator access to /admin/users and /admin/system/status."""
        _, _, admin = self.auth_svc.register_user("admin_user@example.com", "AdminPass123", "Admin User", role="admin")
        admin_token = self.auth_svc.create_token(admin["user_id"], admin["email"], admin["role"])

        # Admin accesses /admin/users -> 200 OK
        res_admin_users = self.client.get("/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_admin_users.status_code, 200)
        self.assertTrue(len(res_admin_users.json()) >= 1)

        # Admin accesses /admin/system/status -> 200 OK
        res_status = self.client.get("/admin/system/status", headers={"Authorization": f"Bearer {admin_token}"})
        self.assertEqual(res_status.status_code, 200)
        telemetry = res_status.json()
        self.assertIn("total_cases", telemetry)
        self.assertIn("vision_model_status", telemetry)
        self.assertEqual(telemetry["vision_model_status"], "active")

    def test_05_signup_role_escalation_prevented(self):
        """Verifies public signup ignores requested 'admin' role and forces 'farmer'."""
        signup_payload = {
            "email": "hacker_attempt@example.com",
            "password": "Password123",
            "full_name": "Privilege Escalation Attempt",
            "role": "admin"  # Attempt to create admin directly
        }
        res = self.client.post("/auth/signup", json=signup_payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["user"]["role"], "farmer", "Public signup must ALWAYS enforce farmer role")

    def test_06_admin_search_and_role_governance(self):
        """Verifies admin user search, role updates, and last-owner protection."""
        # 1. Bootstrap owner
        ok, _, owner = self.auth_svc.bootstrap_owner("owner_test@example.com", "OwnerPass123", "Project Owner")
        self.assertTrue(ok)
        owner_token = self.auth_svc.create_token(owner["user_id"], owner["email"], "owner")

        # 2. Register farmer
        _, _, farmer = self.auth_svc.register_user("farmer_test@example.com", "FarmerPass123", "Farmer Test")
        farmer_token = self.auth_svc.create_token(farmer["user_id"], farmer["email"], "farmer")

        # 3. Farmer cannot search users or update roles
        res_search_farmer = self.client.get("/admin/users/search?query=farmer", headers={"Authorization": f"Bearer {farmer_token}"})
        self.assertEqual(res_search_farmer.status_code, 403)

        res_role_farmer = self.client.post(
            f"/admin/users/{farmer['user_id']}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {farmer_token}"}
        )
        self.assertEqual(res_role_farmer.status_code, 403)

        # 4. Owner can search users
        res_search_owner = self.client.get("/admin/users/search?query=farmer", headers={"Authorization": f"Bearer {owner_token}"})
        self.assertEqual(res_search_owner.status_code, 200)
        results = res_search_owner.json()
        self.assertTrue(any(u["email"] == "farmer_test@example.com" for u in results))

        # 5. Owner promotes farmer to admin
        res_promote = self.client.post(
            f"/admin/users/{farmer['user_id']}/role",
            json={"role": "admin"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        self.assertEqual(res_promote.status_code, 200)
        self.assertIn("updated to 'admin'", res_promote.json()["message"])

        # 6. Attempt to demote the only owner -> rejected
        res_demote_owner = self.client.post(
            f"/admin/users/{owner['user_id']}/role",
            json={"role": "farmer"},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        self.assertEqual(res_demote_owner.status_code, 400)
        self.assertIn("cannot demote the last remaining active project owner", res_demote_owner.json()["detail"].lower())

    def test_07_account_status_and_audit_log(self):
        """Verifies account suspension, login denial, and audit log generation."""
        # 1. Bootstrap owner
        _, _, owner = self.auth_svc.bootstrap_owner("owner_audit@example.com", "OwnerPass123", "Chief Auditor")
        owner_token = self.auth_svc.create_token(owner["user_id"], owner["email"], "owner")

        # 2. Register farmer
        _, _, farmer = self.auth_svc.register_user("suspend_me@example.com", "Pass12345", "Suspended Farmer")

        # 3. Owner suspends farmer account
        res_suspend = self.client.post(
            f"/admin/users/{farmer['user_id']}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        self.assertEqual(res_suspend.status_code, 200)

        # 4. Suspended farmer cannot login
        res_login_suspended = self.client.post("/auth/login", json={
            "email": "suspend_me@example.com",
            "password": "Pass12345"
        })
        self.assertEqual(res_login_suspended.status_code, 401)
        self.assertIn("deactivated", res_login_suspended.json()["detail"].lower())

        # 5. Owner cannot deactivate self
        res_self_suspend = self.client.post(
            f"/admin/users/{owner['user_id']}/status",
            json={"is_active": False},
            headers={"Authorization": f"Bearer {owner_token}"}
        )
        self.assertEqual(res_self_suspend.status_code, 400)

        # 6. Owner views audit logs
        res_logs = self.client.get("/admin/audit-logs", headers={"Authorization": f"Bearer {owner_token}"})
        self.assertEqual(res_logs.status_code, 200)
        logs = res_logs.json()
        self.assertTrue(len(logs) >= 2)
        actions = [log["action"] for log in logs]
        self.assertIn("OWNER_BOOTSTRAP", actions)
        self.assertIn("STATUS_CHANGE", actions)

    def test_08_deleted_user_token_immediately_rejected(self):
        """Verifies that if a user account is deleted, existing tokens are immediately rejected with HTTP 401."""
        _, _, user = self.auth_svc.register_user("to_be_deleted@example.com", "Password123", "Deleted User")
        token = self.auth_svc.create_token(user["user_id"], user["email"], user["role"])

        # Token works initially
        res_me = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me.status_code, 200)

        # Delete user directly from database
        with self.auth_svc._connection() as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?;", (user["user_id"],))
            conn.commit()

        # Token must now be rejected with HTTP 401
        res_me_after = self.client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_me_after.status_code, 401)
        self.assertIn("does not exist", res_me_after.json()["detail"].lower())


if __name__ == "__main__":
    unittest.main()

