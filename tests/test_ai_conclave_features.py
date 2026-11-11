"""
Unit tests for AI Conclave Feature Suite:
- Feature 2: Low-confidence detection and human-review guidance
- Feature 4: Farmer Social Network (observations, comments, treatment outcome tracking)
- Feature 5: Cooperative Multi-Region Comparison (Jammu vs partner grids)
"""
import unittest
from fastapi.testclient import TestClient
from src.api.app import app
from src.api.routes import build_diagnosis_response_from_state
from src.services.case_sharing_service import get_case_sharing_service
from src.services.cooperative_service import get_cooperative_service


class TestAIConclaveFeatures(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_low_confidence_policy_in_diagnosis_response(self):
        """Verify that confidence < 0.65 flags is_low_confidence and sets guidance instructions."""
        low_conf_state = {
            "workflow_status": "completed",
            "primary_diagnosis": "Tomato___Late_blight",
            "diagnosis_confidence": 0.54,
            "assigned_severity": "moderate",
            "epidemic_risk": "HIGH",
            "plan_urgency": "high",
            "final_output": {
                "primary_diagnosis": "Tomato___Late_blight",
                "diagnosis_confidence": 0.54,
                "assigned_severity": "moderate",
                "epidemic_risk": "HIGH",
                "is_verified": False,
                "requires_manual_review": True
            }
        }
        resp = build_diagnosis_response_from_state("CASE-LOWCONF-01", low_conf_state)
        self.assertTrue(resp.is_low_confidence)
        self.assertTrue(resp.requires_manual_review)
        self.assertIsNotNone(resp.low_confidence_guidance)
        self.assertIn("below 65%", resp.low_confidence_guidance)
        self.assertIn("diffused natural light", resp.low_confidence_guidance)

        # High confidence case
        high_conf_state = {
            "workflow_status": "completed",
            "primary_diagnosis": "Tomato___Late_blight",
            "diagnosis_confidence": 0.94,
            "final_output": {
                "primary_diagnosis": "Tomato___Late_blight",
                "diagnosis_confidence": 0.94,
                "is_verified": True,
                "requires_manual_review": False
            }
        }
        resp_high = build_diagnosis_response_from_state("CASE-HIGHCONF-01", high_conf_state)
        self.assertFalse(resp_high.is_low_confidence)
        self.assertFalse(resp_high.requires_manual_review)
        self.assertIsNone(resp_high.low_confidence_guidance)

    def test_farmer_observations_and_comments(self):
        """Test posting and retrieving community observations with strict AI-vs-human separation."""
        case_id = "CASE-COMMUNITY-TEST-01"

        # 1. Add human farmer observation
        payload_farmer = {
            "author_id": "farmer_kuldeep",
            "comment_text": "Sprayed copper oxychloride 48 hours ago; lesion margins stopped expanding.",
            "author_role": "farmer",
            "is_ai": False
        }
        resp = self.client.post(f"/cases/{case_id}/comments", json=payload_farmer)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["case_id"], case_id)
        self.assertEqual(data["author_id"], "farmer_kuldeep")
        self.assertFalse(data["is_ai"])
        self.assertIn("CMT-", data["comment_id"])

        # 2. Add AI assistance observation
        payload_ai = {
            "author_id": "agrimind_critic",
            "comment_text": "Citations indicate copper sprays must maintain 7-day reapplication under rain.",
            "author_role": "agrimind_agent",
            "is_ai": True
        }
        resp_ai = self.client.post(f"/cases/{case_id}/comments", json=payload_ai)
        self.assertEqual(resp_ai.status_code, 201)
        self.assertTrue(resp_ai.json()["is_ai"])

        # 3. Retrieve all comments for the case
        get_resp = self.client.get(f"/cases/{case_id}/comments")
        self.assertEqual(get_resp.status_code, 200)
        comments = get_resp.json()
        self.assertGreaterEqual(len(comments), 2)
        # Verify distinction
        farmer_comments = [c for c in comments if not c["is_ai"]]
        ai_comments = [c for c in comments if c["is_ai"]]
        self.assertGreaterEqual(len(farmer_comments), 1)
        self.assertGreaterEqual(len(ai_comments), 1)

    def test_treatment_outcome_tracking(self):
        """Test recording and updating treatment outcome ('helped', 'did_not_help', 'pending')."""
        case_id = "CASE-OUTCOME-TEST-01"

        # 1. Initial outcome report
        outcome_payload = {
            "farmer_id": "farmer_kuldeep",
            "outcome": "helped",
            "details": "Foliar blight slowed significantly after drip irrigation conversion and mancozeb."
        }
        post_resp = self.client.post(f"/cases/{case_id}/outcome", json=outcome_payload)
        self.assertEqual(post_resp.status_code, 200)
        result = post_resp.json()
        self.assertEqual(result["case_id"], case_id)
        self.assertEqual(result["outcome"], "helped")
        self.assertIn("mancozeb", result["details"])

        # 2. Retrieve outcome
        get_resp = self.client.get(f"/cases/{case_id}/outcome")
        self.assertEqual(get_resp.status_code, 200)
        fetched = get_resp.json()
        self.assertEqual(fetched["outcome"], "helped")
        self.assertEqual(fetched["farmer_id"], "farmer_kuldeep")

    def test_cooperative_multi_region_comparison(self):
        """Test regional comparison endpoint distinguishes live pilot from simulated partner nodes."""
        resp = self.client.get("/cooperative/comparison")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertFalse(data["is_live_partnership"])
        self.assertIn("Multi-cooperative comparison", data["disclaimer"])
        self.assertEqual(len(data["regions"]), 3)

        region_names = [r["region_name"] for r in data["regions"]]
        self.assertTrue(any("Jammu" in name for name in region_names))
        self.assertTrue(any("Punjab" in name for name in region_names))
        self.assertTrue(any("Himachal" in name for name in region_names))

        # Check status labeling
        jammu_region = next(r for r in data["regions"] if "Jammu" in r["region_name"])
        self.assertTrue(jammu_region["is_local_pilot"])
        self.assertIn("Live Community Pilot", jammu_region["data_status"])

        sim_regions = [r for r in data["regions"] if not r["is_local_pilot"]]
        for sim in sim_regions:
            self.assertIn("Simulated Partner Node", sim["data_status"])


if __name__ == "__main__":
    unittest.main()
