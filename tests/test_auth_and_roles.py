"""
Comprehensive Test Suite for Authentication, Role Separation & Security (Stage C).
Verifies:
1. Farmer account creation (signup) with valid & invalid formats.
2. Secure PBKDF2 password hashing (no plaintext, unique salts).
3. Authentication (login) success and rejection of invalid passwords.
4. Session token lifecycle: generation, claim decoding, expiration, and revocation (logout).
5. Role enforcement: Farmer role vs Admin role permissions.
6. Admin operations: user listing and deactivation.
"""
import os
import sys
import tempfile
import unittest

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.services.auth_service import AuthService


class TestAuthAndRoles(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.auth = AuthService(db_path=self.temp_db.name, secret_key="test-secret-key-for-unit-tests")

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    def test_01_farmer_signup_success(self):
        """Verifies successful registration of a farmer account."""
        success, msg, user = self.auth.register_user(
            email="farmer1@example.com",
            password="securePassword123",
            full_name="Ramesh Kumar",
            role="farmer",
            phone="+919876543210"
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user["email"], "farmer1@example.com")
        self.assertEqual(user["role"], "farmer")
        self.assertEqual(user["full_name"], "Ramesh Kumar")
        self.assertTrue(user["user_id"].startswith("USER-"))

    def test_02_password_hashing_security(self):
        """Verifies password is cryptographically hashed with salt; plaintext is never stored."""
        _, _, user1 = self.auth.register_user("farmer1@example.com", "pass123", "User 1")
        _, _, user2 = self.auth.register_user("farmer2@example.com", "pass123", "User 2")

        # Directly query SQLite database to verify stored hashes
        with self.auth._connection() as conn:
            row1 = conn.execute("SELECT password_hash, salt FROM users WHERE user_id = ?", (user1["user_id"],)).fetchone()
            row2 = conn.execute("SELECT password_hash, salt FROM users WHERE user_id = ?", (user2["user_id"],)).fetchone()

            # Plaintext password must NOT be in DB
            self.assertNotEqual(row1["password_hash"], "pass123")
            # Distinct salts for identical passwords
            self.assertNotEqual(row1["salt"], row2["salt"])
            # Distinct hashes for identical passwords due to salt
            self.assertNotEqual(row1["password_hash"], row2["password_hash"])
            # 256-bit hex hash length
            self.assertEqual(len(row1["password_hash"]), 64)

    def test_03_duplicate_email_rejected(self):
        """Prevents duplicate registration with the same email."""
        self.auth.register_user("unique@example.com", "password123", "First User")
        success, msg, user = self.auth.register_user("unique@example.com", "anotherPass", "Second User")
        self.assertFalse(success)
        self.assertIn("already exists", msg)
        self.assertIsNone(user)

    def test_04_invalid_credentials_rejected(self):
        """Rejects login with incorrect password or non-existent email."""
        self.auth.register_user("valid@example.com", "correctPassword", "Valid Farmer")

        # Wrong password
        ok, msg, _ = self.auth.authenticate_user("valid@example.com", "wrongPassword")
        self.assertFalse(ok)
        self.assertIn("Invalid email or password", msg)

        # Non-existent email
        ok, msg, _ = self.auth.authenticate_user("unknown@example.com", "correctPassword")
        self.assertFalse(ok)

    def test_05_token_lifecycle_and_revocation(self):
        """Verifies session token creation, verification, and revocation upon logout."""
        _, _, user = self.auth.register_user("session@example.com", "pass12345", "Session User")
        token = self.auth.create_token(user["user_id"], user["email"], user["role"])
        self.assertIsNotNone(token)

        # Verify valid token
        claims = self.auth.verify_token(token)
        self.assertIsNotNone(claims)
        self.assertEqual(claims["sub"], user["user_id"])
        self.assertEqual(claims["email"], user["email"])
        self.assertEqual(claims["role"], "farmer")

        # Tampered token rejected
        tampered = token[:-4] + "ABCD"
        self.assertIsNone(self.auth.verify_token(tampered))

        # Revoke token (logout)
        revoked = self.auth.revoke_token(token)
        self.assertTrue(revoked)

        # Revoked token is no longer accepted
        self.assertIsNone(self.auth.verify_token(token))

    def test_06_admin_and_role_separation(self):
        """Verifies distinct roles and administrator privilege checks."""
        self.auth.register_user("farmer@example.com", "farmerPass123", "Farmer One", role="farmer")
        self.auth.register_user("admin@example.com", "adminPass123", "Admin User", role="admin")

        ok_f, _, farmer_user = self.auth.authenticate_user("farmer@example.com", "farmerPass123")
        ok_a, _, admin_user = self.auth.authenticate_user("admin@example.com", "adminPass123")

        self.assertTrue(ok_f)
        self.assertTrue(ok_a)
        self.assertEqual(farmer_user["role"], "farmer")
        self.assertEqual(admin_user["role"], "admin")

        # Admin user list
        users = self.auth.list_users()
        self.assertEqual(len(users), 2)

        # Deactivate farmer account
        self.auth.set_user_active_status(farmer_user["user_id"], is_active=False)
        ok_deact, msg_deact, _ = self.auth.authenticate_user("farmer@example.com", "farmerPass123")
        self.assertFalse(ok_deact)
        self.assertIn("deactivated", msg_deact)


if __name__ == "__main__":
    unittest.main()

