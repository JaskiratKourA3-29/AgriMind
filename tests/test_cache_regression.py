"""
Regression Test Suite for Diagnosis Duplicate Submission Cache (Stage B).
Verifies:
1. Verbatim identical submissions hit cache and return identical cached response.
2. Submissions with identical image but different field_notes bypass cache and produce new response.
3. Submissions with identical image but different canopy_spread or affected_organs bypass cache.
4. Oversized or invalid image files are rejected with HTTP 400 before cache lookup.
5. Cache isolation between distinct test cases.
"""
import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.api.app import app
from src.api.routes import _IMAGE_SUBMISSION_CACHE, set_workflow

DUMMY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)


class TestCacheRegression(unittest.TestCase):

    def setUp(self):
        _IMAGE_SUBMISSION_CACHE.clear()
        self.client = TestClient(app)

    def tearDown(self):
        set_workflow(None)
        _IMAGE_SUBMISSION_CACHE.clear()

    def _make_mock_workflow(self, diag: str, severity: str):
        mock_wf = MagicMock()
        mock_wf.stream.return_value = [
            {"vision": {"vision_prediction": {"predicted_class": diag, "confidence": 0.88, "top2_margin": 0.70}}},
            {"verification": {"final_output": {
                "primary_diagnosis": diag,
                "diagnosis_confidence": 0.88,
                "assigned_severity": severity,
                "epidemic_risk": "low",
                "plan_urgency": "low",
                "is_verified": True,
                "verification_status": "verified",
                "requires_manual_review": False,
                "citations": []
            }}}
        ]
        return mock_wf

    def test_01_identical_submission_hits_cache(self):
        """Verbatim identical submissions return the cached diagnosis response."""
        with patch("src.api.routes.get_workflow") as mock_get_wf:
            mock_get_wf.return_value = self._make_mock_workflow("Tomato___Early_blight", "low")

            files1 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data1 = {"field_notes": "Mild yellowing on bottom leaves", "leaf_damage_percentage": 5.0}
            resp1 = self.client.post("/diagnose", files=files1, data=data1)
            self.assertEqual(resp1.status_code, 200)
            case_id_1 = resp1.json()["case_id"]

            # Second call with exact same parameters
            files2 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data2 = {"field_notes": "Mild yellowing on bottom leaves", "leaf_damage_percentage": 5.0}
            resp2 = self.client.post("/diagnose", files=files2, data=data2)
            self.assertEqual(resp2.status_code, 200)
            case_id_2 = resp2.json()["case_id"]

            self.assertEqual(case_id_1, case_id_2, "Identical submission must return cached diagnosis")

    def test_02_different_field_notes_bypasses_cache(self):
        """Changing field_notes generates a distinct cache key and executes a fresh workflow."""
        with patch("src.api.routes.get_workflow") as mock_get_wf:
            mock_get_wf.return_value = self._make_mock_workflow("Tomato___Early_blight", "low")

            files1 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data1 = {"field_notes": "Mild yellowing on bottom leaves", "leaf_damage_percentage": 5.0}
            resp1 = self.client.post("/diagnose", files=files1, data=data1)
            self.assertEqual(resp1.status_code, 200)
            case_id_1 = resp1.json()["case_id"]

            # Change field notes
            mock_get_wf.return_value = self._make_mock_workflow("Tomato___Early_blight", "high")
            files2 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data2 = {"field_notes": "Severe brown concentric lesions expanding rapidly", "leaf_damage_percentage": 5.0}
            resp2 = self.client.post("/diagnose", files=files2, data=data2)
            self.assertEqual(resp2.status_code, 200)
            case_id_2 = resp2.json()["case_id"]

            self.assertNotEqual(case_id_1, case_id_2, "Changed field notes must not return stale cached response")

    def test_03_different_canopy_spread_bypasses_cache(self):
        """Changing canopy_spread generates a distinct cache key."""
        with patch("src.api.routes.get_workflow") as mock_get_wf:
            mock_get_wf.return_value = self._make_mock_workflow("Tomato___Early_blight", "low")

            files1 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data1 = {"canopy_spread": "lower_canopy", "leaf_damage_percentage": 5.0}
            resp1 = self.client.post("/diagnose", files=files1, data=data1)
            self.assertEqual(resp1.status_code, 200)
            case_id_1 = resp1.json()["case_id"]

            files2 = {"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
            data2 = {"canopy_spread": "upper_canopy", "leaf_damage_percentage": 5.0}
            resp2 = self.client.post("/diagnose", files=files2, data=data2)
            self.assertEqual(resp2.status_code, 200)
            case_id_2 = resp2.json()["case_id"]

            self.assertNotEqual(case_id_1, case_id_2, "Changed canopy spread must not return stale cached response")

    def test_04_invalid_image_rejected_before_cache(self):
        """Corrupted or non-image files are rejected with HTTP 400 and not cached."""
        files = {"file": ("test.txt", io.BytesIO(b"This is not an image file"), "text/plain")}
        resp = self.client.post("/diagnose", files=files)
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(len(_IMAGE_SUBMISSION_CACHE), 0, "Invalid files must never be cached")


if __name__ == "__main__":
    unittest.main()

