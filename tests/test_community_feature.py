"""
AgriMind Farmer Community & Social Connection Test Suite.
Verifies:
1. Multi-farmer interaction (Farmer A & Farmer B).
2. Post creation, categorization, search, and pagination.
3. PII privacy protection (no emails/phones in public responses).
4. Comments and threaded replies.
5. Likes / helpful reactions (toggle, prevent duplicate reactions).
6. Accepted useful answer logic (author-only enforcement).
7. Author-only editing isolation.
8. Deletion isolation (farmers cannot delete each other's content).
9. Content reporting and safety.
10. Main Owner & Sub-Owner moderation privileges and audit logs.
"""
import os
import sys
import unittest
import tempfile
from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.services.auth_service import AuthService, set_auth_service
from src.services.community_service import CommunityService, set_community_service
from src.api.case_store import CaseStore, set_case_store


class TestCommunityFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.db_path = os.path.join(cls.temp_dir.name, "community_test.db")
        cls.auth_svc = AuthService(db_path=cls.db_path)
        cls.comm_svc = CommunityService(db_path=cls.db_path)
        cls.case_store = CaseStore(db_path=cls.db_path)

        set_auth_service(cls.auth_svc)
        set_community_service(cls.comm_svc)
        set_case_store(cls.case_store)

        cls.client = TestClient(app)

        # 1. Main Project Owner: Jaskirat Kour
        ok, _, owner_user = cls.auth_svc.register_user(
            email="jaskiratkourjk2005@gmail.com",
            password="OwnerPassword2026!",
            full_name="Jaskirat Kour",
            role="owner",
            phone="+91-9419100001"
        )
        assert ok
        cls.owner_id = owner_user["user_id"]
        cls.owner_token = cls.auth_svc.create_token(cls.owner_id, "jaskiratkourjk2005@gmail.com", "owner")
        cls.owner_headers = {"Authorization": f"Bearer {cls.owner_token}"}

        # 2. Farmer A: Simran Kour
        ok, _, farmer_a = cls.auth_svc.register_user(
            email="2023a1r029@mietjammu.in",
            password="FarmerAPassword2026!",
            full_name="Simran Kour",
            role="farmer",
            phone="+91-9419200002"
        )
        assert ok
        cls.farmer_a_id = farmer_a["user_id"]
        cls.farmer_a_token = cls.auth_svc.create_token(cls.farmer_a_id, "2023a1r029@mietjammu.in", "farmer")
        cls.farmer_a_headers = {"Authorization": f"Bearer {cls.farmer_a_token}"}

        # 3. Farmer B: Ramesh Kumar
        ok, _, farmer_b = cls.auth_svc.register_user(
            email="ramesh_farmer@jammu.in",
            password="FarmerBPassword2026!",
            full_name="Ramesh Kumar (R.S. Pura)",
            role="farmer",
            phone="+91-9419300003"
        )
        assert ok
        cls.farmer_b_id = farmer_b["user_id"]
        cls.farmer_b_token = cls.auth_svc.create_token(cls.farmer_b_id, "ramesh_farmer@jammu.in", "farmer")
        cls.farmer_b_headers = {"Authorization": f"Bearer {cls.farmer_b_token}"}

        # 4. Sub-Owner candidate
        ok, _, sub_candidate = cls.auth_svc.register_user(
            email="deputy_moderator@agrimind.in",
            password="DeputyPassword2026!",
            full_name="Deputy Moderator",
            role="farmer"
        )
        assert ok
        cls.sub_id = sub_candidate["user_id"]
        # Main owner grants sub_owner role with can_moderate_cases
        cls.auth_svc.grant_sub_owner(
            acting_user={"role": "owner", "email": "jaskiratkourjk2005@gmail.com"},
            target_user_id=cls.sub_id,
            permissions=["can_moderate_cases"]
        )
        cls.sub_token = cls.auth_svc.create_token(cls.sub_id, "deputy_moderator@agrimind.in", "sub_owner")
        cls.sub_headers = {"Authorization": f"Bearer {cls.sub_token}"}

    @classmethod
    def tearDownClass(cls):
        set_auth_service(None)
        set_community_service(None)
        set_case_store(None)
        cls.temp_dir.cleanup()

    def test_01_farmer_a_creates_community_post(self):
        """Farmer A creates a crop disease discussion post."""
        payload = {
            "title": "Severe concentric rings on lower tomato leaves",
            "content": "Noticed brown target-shaped spots spreading rapidly on lower canopy after heavy morning dew. Is this early blight?",
            "category": "crop_disease"
        }
        res = self.client.post("/community/posts", json=payload, headers=self.farmer_a_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertTrue(data["post_id"].startswith("POST-"))
        self.assertEqual(data["author_name"], "Simran Kour")
        self.assertEqual(data["category"], "crop_disease")
        self.assertEqual(data["likes_count"], 0)
        self.assertEqual(data["comments_count"], 0)

        # Save post_id for subsequent tests
        TestCommunityFeature.shared_post_id = data["post_id"]

    def test_02_farmer_b_views_feed_with_pii_privacy(self):
        """Farmer B views community feed; Farmer A's post is visible without private email or phone."""
        res = self.client.get("/community/posts?category=crop_disease", headers=self.farmer_b_headers)
        self.assertEqual(res.status_code, 200)
        feed = res.json()
        self.assertGreaterEqual(feed["total_count"], 1)

        post = next((p for p in feed["posts"] if p["post_id"] == self.shared_post_id), None)
        self.assertIsNotNone(post)
        self.assertEqual(post["author_name"], "Simran Kour")
        self.assertEqual(post["category_label"], "Crop Disease")

        # PII Protection check: private email & phone must NOT exist in the response
        raw_text = res.text
        self.assertNotIn("2023a1r029@mietjammu.in", raw_text)
        self.assertNotIn("+91-9419200002", raw_text)

    def test_03_farmer_b_likes_post_and_toggles(self):
        """Farmer B likes Farmer A's post, verifying duplicate prevention and toggle behavior."""
        # 1. Like post
        res_like = self.client.post(f"/community/reactions/post/{self.shared_post_id}", headers=self.farmer_b_headers)
        self.assertEqual(res_like.status_code, 200)
        self.assertEqual(res_like.json()["likes_count"], 1)
        self.assertTrue(res_like.json()["has_liked"])

        # Check single post details from Farmer B's view
        res_detail = self.client.get(f"/community/posts/{self.shared_post_id}", headers=self.farmer_b_headers)
        self.assertEqual(res_detail.json()["likes_count"], 1)
        self.assertTrue(res_detail.json()["has_liked"])

        # Check from Farmer A's view (Farmer A has not liked it)
        res_a_view = self.client.get(f"/community/posts/{self.shared_post_id}", headers=self.farmer_a_headers)
        self.assertEqual(res_a_view.json()["likes_count"], 1)
        self.assertFalse(res_a_view.json()["has_liked"])

        # 2. Toggle unlike
        res_unlike = self.client.post(f"/community/reactions/post/{self.shared_post_id}", headers=self.farmer_b_headers)
        self.assertEqual(res_unlike.json()["likes_count"], 0)
        self.assertFalse(res_unlike.json()["has_liked"])

        # 3. Re-like for state
        self.client.post(f"/community/reactions/post/{self.shared_post_id}", headers=self.farmer_b_headers)

    def test_04_comments_and_threaded_replies(self):
        """Farmer B comments on the post, and Farmer A replies to Farmer B's comment."""
        # Farmer B adds solution comment
        b_comment_payload = {
            "comment_text": "Classic Early Blight (Alternaria solani). Apply copper oxychloride (2.5 g/L) and stake plants to improve airflow."
        }
        res_comm = self.client.post(f"/community/posts/{self.shared_post_id}/comments", json=b_comment_payload, headers=self.farmer_b_headers)
        self.assertEqual(res_comm.status_code, 201)
        b_comment = res_comm.json()
        self.assertEqual(b_comment["author_name"], "Ramesh Kumar (R.S. Pura)")
        TestCommunityFeature.b_comment_id = b_comment["comment_id"]

        # Farmer A replies to Farmer B's comment (threaded reply)
        reply_payload = {
            "comment_text": "Thank you Ramesh! Pruning lower leaves today. Did you see quick recovery?",
            "parent_comment_id": self.b_comment_id
        }
        res_reply = self.client.post(f"/community/posts/{self.shared_post_id}/comments", json=reply_payload, headers=self.farmer_a_headers)
        self.assertEqual(res_reply.status_code, 201)
        reply = res_reply.json()
        self.assertEqual(reply["parent_comment_id"], self.b_comment_id)
        TestCommunityFeature.a_reply_id = reply["comment_id"]

        # Verify hierarchical listing
        res_list = self.client.get(f"/community/posts/{self.shared_post_id}/comments", headers=self.farmer_b_headers)
        self.assertEqual(res_list.status_code, 200)
        comments = res_list.json()
        self.assertEqual(len(comments), 1)  # 1 top-level comment
        self.assertEqual(comments[0]["comment_id"], self.b_comment_id)
        self.assertEqual(len(comments[0]["replies"]), 1)  # 1 nested threaded reply
        self.assertEqual(comments[0]["replies"][0]["comment_id"], self.a_reply_id)

    def test_05_solution_acceptance_author_only_enforcement(self):
        """Only the post author (Farmer A) can accept a solution; Farmer B is denied."""
        # Farmer B tries to mark their own answer as accepted -> 403 Forbidden
        res_b_attempt = self.client.post(
            f"/community/posts/{self.shared_post_id}/comments/{self.b_comment_id}/accept",
            headers=self.farmer_b_headers
        )
        self.assertEqual(res_b_attempt.status_code, 403)

        # Farmer A (post author) marks Farmer B's answer as accepted -> 200 OK
        res_a_accept = self.client.post(
            f"/community/posts/{self.shared_post_id}/comments/{self.b_comment_id}/accept",
            headers=self.farmer_a_headers
        )
        self.assertEqual(res_a_accept.status_code, 200)

        # Verify comment is accepted and post is marked resolved
        post_res = self.client.get(f"/community/posts/{self.shared_post_id}")
        self.assertTrue(post_res.json()["is_resolved"])

        comments_res = self.client.get(f"/community/posts/{self.shared_post_id}/comments")
        self.assertTrue(comments_res.json()[0]["is_accepted"])

    def test_06_content_ownership_editing_isolation(self):
        """Farmers can only edit their own posts; unauthorized editing is blocked."""
        # Farmer B tries to edit Farmer A's post -> 403 Forbidden
        res_b_edit = self.client.put(
            f"/community/posts/{self.shared_post_id}",
            json={"title": "Hacked title by Farmer B"},
            headers=self.farmer_b_headers
        )
        self.assertEqual(res_b_edit.status_code, 403)

        # Farmer A edits own post -> 200 OK
        res_a_edit = self.client.put(
            f"/community/posts/{self.shared_post_id}",
            json={"title": "Severe concentric rings on lower tomato leaves [RESOLVED]"},
            headers=self.farmer_a_headers
        )
        self.assertEqual(res_a_edit.status_code, 200)
        self.assertIn("[RESOLVED]", res_a_edit.json()["title"])

    def test_07_content_reporting(self):
        """Farmers can report inappropriate or misleading content."""
        report_payload = {
            "target_type": "post",
            "target_id": self.shared_post_id,
            "reason": "misleading",
            "details": "Testing report safety pipeline"
        }
        res_rep = self.client.post("/community/reports", json=report_payload, headers=self.farmer_b_headers)
        self.assertEqual(res_rep.status_code, 200)

        # Non-moderators cannot view reports -> 403
        res_view_denied = self.client.get("/community/reports", headers=self.farmer_b_headers)
        self.assertEqual(res_view_denied.status_code, 403)

        # Main Owner views reports -> 200 OK
        res_view_owner = self.client.get("/community/reports", headers=self.owner_headers)
        self.assertEqual(res_view_owner.status_code, 200)
        self.assertGreaterEqual(len(res_view_owner.json()), 1)

    def test_08_deletion_isolation_and_moderator_privileges(self):
        """Farmers cannot delete each other's content, but authorized moderators can."""
        # Farmer B tries to delete Farmer A's post -> 403 Forbidden
        res_del_denied = self.client.delete(f"/community/posts/{self.shared_post_id}", headers=self.farmer_b_headers)
        self.assertEqual(res_del_denied.status_code, 403)

        # Sub-Owner with can_moderate_cases permission deletes the post -> 200 OK
        res_sub_del = self.client.delete(f"/community/posts/{self.shared_post_id}", headers=self.sub_headers)
        self.assertEqual(res_sub_del.status_code, 200)

        # Verify post is removed from feed
        res_get = self.client.get(f"/community/posts/{self.shared_post_id}")
        self.assertEqual(res_get.status_code, 404)

        # Verify audit log was recorded for moderation action
        audit_logs = self.auth_svc.get_audit_logs(limit=10)
        actions = [log["action"] for log in audit_logs]
        self.assertIn("COMMUNITY_POST_MODERATED", actions)


if __name__ == "__main__":
    unittest.main()

