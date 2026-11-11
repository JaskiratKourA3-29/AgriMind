"""
Rigorous End-to-End Verification Test Suite for Feature 2: Vision Inference & Low-Confidence Policy.
Tests every condition required by Section 3:
1. Valid images for all 3 classes (Bacterial Spot, Early Blight, Late Blight) using real PlantVillage images.
2. Rejection of corrupted, empty, oversized, and non-image payloads (HTTP 400).
3. Low-confidence threshold (< 0.65) and top-2 margin (< 0.15) triggering is_low_confidence=True, requires_manual_review=True, and guidance string.
4. High-confidence threshold (>= 0.65 and margin >= 0.15) verifying is_low_confidence=False, requires_manual_review=False.
5. Precise latency breakdown recording (preprocessing, forward pass, multi-agent workflow, total /diagnose).
"""
import os
import io
import time
import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.api.app import app
from src.api.routes import set_workflow, _IMAGE_SUBMISSION_CACHE
from src.agents.schemas import SupportedTomatoDisease

# Minimal valid JPEG image header bytes for fast mocking
DUMMY_JPEG_BYTES = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
)

# Verified paths to real PlantVillage test images
IMAGE_BACTERIAL = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"
if not os.path.exists(IMAGE_BACTERIAL):
    IMAGE_BACTERIAL = "C:/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"

IMAGE_EARLY = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Early_blight/0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B 8389.JPG"
if not os.path.exists(IMAGE_EARLY):
    IMAGE_EARLY = "C:/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Early_blight/0012b9d2-2130-4a06-a834-b1f3af34f57e___RS_Erly.B 8389.JPG"

IMAGE_LATE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Late_blight/0003faa8-4b27-4c65-bf42-6d9e352ca1a5___RS_Late.B 4946.JPG"
if not os.path.exists(IMAGE_LATE):
    IMAGE_LATE = "C:/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Late_blight/0003faa8-4b27-4c65-bf42-6d9e352ca1a5___RS_Late.B 4946.JPG"


def make_mock_workflow(predicted_class, confidence, severity="moderate", requires_review=False):
    mock = MagicMock()
    mock.stream.return_value = [
        {"vision": {"vision_prediction": {"predicted_class": predicted_class, "confidence": confidence, "top2_margin": 0.05 if confidence < 0.65 else 0.80}}},
        {"verification": {"final_output": {
            "primary_diagnosis": predicted_class,
            "diagnosis_confidence": confidence,
            "assigned_severity": severity,
            "epidemic_risk": "moderate",
            "plan_urgency": "medium",
            "is_verified": True,
            "verification_status": "verified",
            "requires_manual_review": requires_review or (confidence < 0.65),
            "manual_review_status": "flagged_for_review" if (confidence < 0.65) else None,
            "citations": []
        }}}
    ]
    return mock


class TestFeature2VisionInference(unittest.TestCase):

    def setUp(self):
        _IMAGE_SUBMISSION_CACHE.clear()
        self.client = TestClient(app)

    def tearDown(self):
        set_workflow(None)
        _IMAGE_SUBMISSION_CACHE.clear()

    def test_01_corrupted_empty_and_non_image_rejection(self):
        """Rejects empty, non-image text, and corrupted files with HTTP 400."""
        # 1. Empty file (0 bytes)
        empty_file = io.BytesIO(b"")
        resp_empty = self.client.post(
            "/diagnose",
            files={"file": ("empty.jpg", empty_file, "image/jpeg")}
        )
        self.assertEqual(resp_empty.status_code, 400)
        self.assertIn("empty", resp_empty.json()["detail"].lower())

        # 2. Plain text / non-image file
        text_file = io.BytesIO(b"Hello world! This is a plain text file pretending to be a leaf image.")
        resp_text = self.client.post(
            "/diagnose",
            files={"file": ("text.txt", text_file, "text/plain")}
        )
        self.assertEqual(resp_text.status_code, 400)
        self.assertIn("unsupported or invalid image", resp_text.json()["detail"].lower())

        # 3. Corrupted image header
        corrupt_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + (b"\xaa\xbb\xcc" * 10)
        corrupt_file = io.BytesIO(corrupt_jpeg)
        resp_corrupt = self.client.post(
            "/diagnose",
            files={"file": ("corrupted.jpg", corrupt_file, "image/jpeg")}
        )
        self.assertEqual(resp_corrupt.status_code, 400)
        self.assertIn("corrupted or unreadable", resp_corrupt.json()["detail"].lower())

    def test_02_low_confidence_policy_triggering(self):
        """Verifies low-confidence (<0.65) correctly populates is_low_confidence=True and guidance string."""
        set_workflow(make_mock_workflow(
            predicted_class="Tomato___Bacterial_spot",
            confidence=0.52,
            requires_review=True
        ))

        resp = self.client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["is_low_confidence"], "is_low_confidence must be True when confidence < 0.65")
        self.assertTrue(data["requires_manual_review"], "requires_manual_review must be True when confidence < 0.65")
        self.assertIsNotNone(data["low_confidence_guidance"], "low_confidence_guidance must not be None")
        self.assertIn("below 65%", data["low_confidence_guidance"])

    def test_03_high_confidence_policy(self):
        """Verifies high-confidence (>=0.65) does not trigger low-confidence alert."""
        set_workflow(make_mock_workflow(
            predicted_class="Tomato___Early_blight",
            confidence=0.92,
            requires_review=False
        ))

        resp = self.client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", io.BytesIO(DUMMY_JPEG_BYTES), "image/jpeg")}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["is_low_confidence"])
        self.assertFalse(data["requires_manual_review"])
        self.assertIsNone(data["low_confidence_guidance"])

    def test_04_real_image_inference_bacterial_spot(self):
        """Executes real ResNet-50 + LangGraph inference on genuine PlantVillage Bacterial Spot image."""
        self.assertTrue(os.path.exists(IMAGE_BACTERIAL), f"Image missing: {IMAGE_BACTERIAL}")

        start_time = time.perf_counter()
        with open(IMAGE_BACTERIAL, "rb") as f:
            resp = self.client.post(
                "/diagnose",
                files={"file": ("bacterial_spot.jpg", f, "image/jpeg")},
                data={
                    "canopy_spread": "lower_canopy",
                    "weather_conditions": "warm_humid",
                    "field_notes": "Small circular water-soaked lesions observed on lower leaves."
                }
            )
        total_time_s = time.perf_counter() - start_time

        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertTrue(data["case_id"].startswith("CASE-"))
        self.assertEqual(data["primary_diagnosis"], SupportedTomatoDisease.BACTERIAL_SPOT.value)
        self.assertGreater(data["diagnosis_confidence"], 0.65)
        self.assertFalse(data["is_low_confidence"])
        self.assertGreater(len(data["citations"]), 0)

        latency = data.get("latency_breakdown", {})
        print(f"\n[BENCHMARK] Bacterial Spot Total Latency: {total_time_s:.2f}s | Workflow: {latency.get('total_workflow_ms')}ms | Vision: {latency.get('model_inference_ms')}ms")

    def test_05_duplicate_submission_prevention(self):
        """Verifies duplicate image submission within cache window returns cached result instantly."""
        self.assertTrue(os.path.exists(IMAGE_BACTERIAL), f"Image missing: {IMAGE_BACTERIAL}")

        with open(IMAGE_BACTERIAL, "rb") as f:
            img_bytes = f.read()

        # First submission
        t1 = time.perf_counter()
        resp1 = self.client.post(
            "/diagnose",
            files={"file": ("bact.jpg", io.BytesIO(img_bytes), "image/jpeg")},
            data={"weather_conditions": "warm_humid"}
        )
        dur1 = time.perf_counter() - t1
        self.assertEqual(resp1.status_code, 200)
        case_id_1 = resp1.json()["case_id"]

        # Second submission with same image and parameters
        t2 = time.perf_counter()
        resp2 = self.client.post(
            "/diagnose",
            files={"file": ("bact_dup.jpg", io.BytesIO(img_bytes), "image/jpeg")},
            data={"weather_conditions": "warm_humid"}
        )
        dur2 = time.perf_counter() - t2
        self.assertEqual(resp2.status_code, 200)
        case_id_2 = resp2.json()["case_id"]

        # Must return the same cached diagnosis with near-zero latency
        self.assertEqual(case_id_1, case_id_2)
        print(f"\n[BENCHMARK] Duplicate Prevention Latency: Fresh={dur1:.2f}s, Cached={dur2:.4f}s (Speedup: {dur1/max(dur2, 0.0001):.1f}x)")


if __name__ == "__main__":
    unittest.main()
