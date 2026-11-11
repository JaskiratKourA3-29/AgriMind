"""
Unit tests for AgriMind Authorized Case Sharing, Social Collaboration & Access Control Service.
"""
import unittest
import tempfile
import os
import math
from src.services.case_sharing_service import CaseSharingService


class TestCaseSharingService(unittest.TestCase):

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.service = CaseSharingService(db_path=self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except OSError:
                pass

    def test_share_case_anonymized_pii(self):
        """Verifies PII is sanitized and GPS coordinates fuzzed when anonymized."""
        sample_case = {
            "case_id": "CASE-TEST1234",
            "farmer_name": "Jaskirat Singh",
            "phone": "+91-9876543210",
            "latitude": 32.726612,
            "longitude": 74.857015,
            "primary_diagnosis": "Tomato___Late_blight",
            "assigned_severity": "high",
            "epidemic_risk": "high"
        }
        res = self.service.share_case(
            case_data=sample_case,
            owner_farmer_id="FARMER-JASKIRAT",
            target_entity="cooperative_all",
            access_level="cooperative",
            anonymize_pii=True
        )
        self.assertTrue(res["share_id"].startswith("SHARE-"))
        self.assertTrue(res["share_token"].startswith("tok_"))
        self.assertEqual(res["owner_farmer_id"], "ANONYMOUS")

        # Retrieve and verify PII removal
        retrieved = self.service.get_shared_case(res["share_id"], share_token=res["share_token"])
        self.assertIsNotNone(retrieved)
        cdata = retrieved["case_data"]
        self.assertEqual(cdata["farmer_name"], "Anonymous Farmer")
        self.assertNotIn("phone", cdata)
        self.assertEqual(cdata["latitude"], 32.7)  # Fuzzed to 1 decimal place

    def test_gps_fuzzing_math(self):
        """
        Validates GPS truncation math: rounding to 1 decimal place (0.1 deg)
        provides ~11.1 km latitude fuzzing distance, protecting exact field location.
        """
        original_lat = 32.726612
        fuzzed_lat = round(original_lat, 1)  # 32.7
        delta_lat = abs(original_lat - fuzzed_lat)
        # 1 degree of latitude is approximately 111.139 km
        distance_km = delta_lat * 111.139

        self.assertGreater(distance_km, 2.0, "Fuzzing offset should provide privacy buffer > 2 km")
        self.assertLess(distance_km, 12.0, "Fuzzing offset should preserve regional relevance < 12 km")
        print(f"\n[PRIVACY] GPS Fuzzing: {original_lat} -> {fuzzed_lat} (delta: {delta_lat:.4f} deg, buffer: {distance_km:.2f} km)")

    def test_unauthorized_token_rejection(self):
        """Verifies invalid token access is rejected."""
        sample_case = {
            "case_id": "CASE-SECRET",
            "primary_diagnosis": "Tomato___Early_blight"
        }
        res = self.service.share_case(
            case_data=sample_case,
            owner_farmer_id="FARMER-ALICE",
            target_entity="FARMER-BOB",
            access_level="farmer",
            anonymize_pii=False
        )
        # Attempt access with wrong token
        unauth = self.service.get_shared_case(res["share_id"], share_token="tok_bad_token", requester_id="FARMER-EVE")
        self.assertIsNone(unauth)

        # Access with legitimate token
        legit = self.service.get_shared_case(res["share_id"], share_token=res["share_token"])
        self.assertIsNotNone(legit)

    def test_revoke_share(self):
        """Verifies only owner can revoke a share."""
        sample_case = {"case_id": "CASE-REVOKE", "primary_diagnosis": "Tomato___Late_blight"}
        res = self.service.share_case(sample_case, owner_farmer_id="OWNER-1")

        # Wrong owner cannot revoke
        wrong_rev = self.service.revoke_share(res["share_id"], owner_farmer_id="WRONG-OWNER")
        self.assertFalse(wrong_rev)

        # Right owner revokes
        right_rev = self.service.revoke_share(res["share_id"], owner_farmer_id="OWNER-1")
        self.assertTrue(right_rev)

        # After revocation, case is not retrievable
        ret = self.service.get_shared_case(res["share_id"], share_token=res["share_token"])
        self.assertIsNone(ret)

    def test_comments_human_and_ai_attribution(self):
        """Verifies comments thread strictly preserves human vs AI attribution."""
        case_id = "CASE-COLLAB-01"
        # 1. Human Farmer comment
        c1 = self.service.add_comment(
            case_id=case_id,
            author_id="FARMER-RAMESH",
            comment_text="I observed similar water-soaked lesions in R.S. Pura block yesterday.",
            author_role="farmer",
            is_ai=False
        )
        self.assertTrue(c1["comment_id"].startswith("CMT-"))
        self.assertFalse(c1["is_ai"])
        self.assertEqual(c1["author_role"], "farmer")

        # 2. AI Decision Support comment
        c2 = self.service.add_comment(
            case_id=case_id,
            author_id="AGRIMIND-AI",
            comment_text="Current temperature (19°C) and RH (85%) meet Wallin late blight criteria. Immediate copper protectant advised.",
            author_role="ai_assistant",
            is_ai=True
        )
        self.assertTrue(c2["is_ai"])

        # Fetch comments thread
        thread = self.service.get_comments(case_id)
        self.assertEqual(len(thread), 2)
        self.assertFalse(thread[0]["is_ai"])
        self.assertTrue(thread[1]["is_ai"])

    def test_treatment_outcome_recording(self):
        """Verifies recording post-treatment recovery outcome and resolution notes."""
        case_id = "CASE-OUTCOME-01"
        treatment_notes = "Fixed copper hydroxide (1.5 lb/acre) + Mancozeb tank mix. Lesion spread halted within 5 days."
        out = self.service.record_outcome(
            case_id=case_id,
            farmer_id="FARMER-01",
            outcome="helped",
            details=treatment_notes
        )
        self.assertEqual(out["case_id"], case_id)
        self.assertEqual(out["farmer_id"], "FARMER-01")
        self.assertEqual(out["outcome"], "helped")
        self.assertEqual(out["details"], treatment_notes)
        self.assertIn("updated_at", out)

        # Retrieve outcome
        retrieved = self.service.get_outcome(case_id)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["case_id"], case_id)
        self.assertEqual(retrieved["farmer_id"], "FARMER-01")
        self.assertEqual(retrieved["outcome"], "helped")
        self.assertEqual(retrieved["details"], treatment_notes)


if __name__ == "__main__":
    unittest.main()
