"""
Unit tests for AgriMind Phase 2: Controlled Background-Masking Diagnostic Experiment.
Validates:
1. Checkpoint integrity and loading without modification.
2. Deterministic leaf segmentation algorithm and diagnostic image generation.
3. Sample alignment and presence of all 28 official test samples.
4. Completeness and validity of all generated visual and JSON artifacts.
5. Exact metrics consistency and agreement calculations across Conditions A, B, and C.
"""
import os
import sys
import json
import csv
import hashlib
import unittest
import numpy as np
from PIL import Image
import torch

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.vision.model import create_model
from scripts.run_background_masking_experiment import (
    segment_leaf,
    create_diagnostic_images,
    CHECKPOINT_PATH,
    OUTPUT_BASE_DIR,
    NEUTRAL_STUDIO_GRAY
)

EXPECTED_CHECKPOINT_HASH = "EB40B4D9FF9BC8278B63392809702FC17DBE701B05974C8A620588AB56C196D5"


class TestPhase2BackgroundMasking(unittest.TestCase):
    """Test suite for Phase 2 background-masking experiment."""

    def test_checkpoint_integrity(self):
        """Authoritative Week 2 checkpoint exists, is unmodified, and loads cleanly in eval mode."""
        self.assertTrue(os.path.exists(CHECKPOINT_PATH), f"Checkpoint missing: {CHECKPOINT_PATH}")

        # Verify SHA-256 hash
        hasher = hashlib.sha256()
        with open(CHECKPOINT_PATH, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        actual_hash = hasher.hexdigest().upper()
        self.assertEqual(actual_hash, EXPECTED_CHECKPOINT_HASH, "Checkpoint hash mismatch!")

        # Verify loading into model
        model = create_model(num_classes=3, pretrained=False)
        ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu")
        model.load_state_dict(ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt)
        model.eval()
        self.assertFalse(model.training)

    def test_segmentation_algorithm_synthetic(self):
        """Tests deterministic leaf segmentation on synthetic test images."""
        # 1. Image with green rectangle on blue sky background
        img_np = np.zeros((100, 100, 3), dtype=np.uint8)
        # Background: sky blue (R=100, G=180, B=240)
        img_np[:, :] = [100, 180, 240]
        # Foreground: green plant leaf (R=50, G=170, B=40)
        img_np[20:80, 20:80] = [50, 170, 40]
        img_pil = Image.fromarray(img_np)

        mask = segment_leaf(img_pil)
        self.assertEqual(mask.shape, (100, 100))
        self.assertEqual(mask.dtype, bool)
        # Center should be identified as leaf
        self.assertTrue(mask[50, 50])
        # Corner sky should be identified as background
        self.assertFalse(mask[5, 5])

        # 2. Test diagnostic image generation
        masked_img, bg_only_img, mask_img = create_diagnostic_images(img_pil, mask)
        self.assertEqual(masked_img.size, (100, 100))
        self.assertEqual(bg_only_img.size, (100, 100))
        self.assertEqual(mask_img.size, (100, 100))

        # Check background fill in Condition B
        masked_arr = np.array(masked_img)
        np.testing.assert_array_equal(masked_arr[5, 5], NEUTRAL_STUDIO_GRAY)
        np.testing.assert_array_equal(masked_arr[50, 50], [50, 170, 40])

        # Check leaf suppression in Condition C
        bg_only_arr = np.array(bg_only_img)
        np.testing.assert_array_equal(bg_only_arr[50, 50], NEUTRAL_STUDIO_GRAY)
        np.testing.assert_array_equal(bg_only_arr[5, 5], [100, 180, 240])

    def test_sample_alignment_and_counts(self):
        """Verifies per_sample_predictions.csv contains exactly 28 aligned rows."""
        csv_path = os.path.join(OUTPUT_BASE_DIR, "per_sample_predictions.csv")
        self.assertTrue(os.path.exists(csv_path), f"CSV missing: {csv_path}")

        rows = []
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for r in reader:
                rows.append(r)

        self.assertEqual(len(rows), 28, f"Expected 28 samples, found {len(rows)}")

        # Verify class counts
        bs_count = sum(1 for r in rows if r["ground_truth"] == "Bacterial_spot")
        eb_count = sum(1 for r in rows if r["ground_truth"] == "Early_blight")
        lb_count = sum(1 for r in rows if r["ground_truth"] == "Late_blight")

        self.assertEqual(bs_count, 9)
        self.assertEqual(eb_count, 9)
        self.assertEqual(lb_count, 10)

        # Verify required columns
        req_cols = [
            "sample_id", "filename", "ground_truth", "leaf_coverage_pct",
            "cond_a_pred", "cond_a_conf", "cond_a_correct",
            "cond_b_pred", "cond_b_conf", "cond_b_correct", "cond_b_changed",
            "cond_c_pred", "cond_c_conf", "cond_c_correct"
        ]
        for col in req_cols:
            self.assertIn(col, rows[0])

    def test_generated_artifacts_completeness(self):
        """All visual figures, masks, and per-sample JSON files exist and are non-empty."""
        subdirs = [
            "original_images",
            "masks",
            "masked_images",
            "background_only",
            "comparison_figures",
            "per_sample_results"
        ]
        for sub in subdirs:
            dp = os.path.join(OUTPUT_BASE_DIR, sub)
            self.assertTrue(os.path.exists(dp), f"Subdirectory missing: {dp}")
            files = os.listdir(dp)
            self.assertEqual(len(files), 28, f"Expected 28 files in {sub}, found {len(files)}")
            for f in files:
                fp = os.path.join(dp, f)
                self.assertGreater(os.path.getsize(fp), 0, f"File is empty: {fp}")

    def test_reports_and_metrics_consistency(self):
        """Verifies report files exist and experiment_metrics.json contains valid values."""
        reports = [
            "phase2_experiment_report.md",
            "bacterial_spot_sample_analysis.md",
            "visual_comparison.md",
            "integrity_check.md",
            "experiment_metrics.json",
            "per_sample_predictions.csv"
        ]
        for rep in reports:
            fp = os.path.join(OUTPUT_BASE_DIR, rep)
            self.assertTrue(os.path.exists(fp), f"Report missing: {fp}")
            self.assertGreater(os.path.getsize(fp), 0, f"Report is empty: {fp}")

        # Check metrics values in JSON
        metrics_json_path = os.path.join(OUTPUT_BASE_DIR, "experiment_metrics.json")
        with open(metrics_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["sample_count"], 28)

        # Baseline Condition A accuracy must reproduce established 39.29%
        self.assertAlmostEqual(data["condition_a_baseline"]["metrics"]["accuracy"], 0.3929, places=4)
        self.assertEqual(data["condition_a_baseline"]["metrics"]["per_class"]["Bacterial_spot"]["recall"], 0.0)

        # Condition B accuracy must be 50.00%
        self.assertAlmostEqual(data["condition_b_masked"]["metrics"]["accuracy"], 0.5000, places=4)
        # Condition B Bacterial spot recall must be 2 / 9 = 0.2222
        self.assertAlmostEqual(data["condition_b_masked"]["metrics"]["per_class"]["Bacterial_spot"]["recall"], 0.2222, places=4)
        self.assertEqual(data["condition_b_masked"]["metrics"]["per_class"]["Bacterial_spot"]["precision"], 1.0)

        # Condition B agreement with A must be 82.14% (23 / 28)
        self.assertAlmostEqual(data["condition_b_masked"]["agreement_with_a_pct"], 82.14, places=2)
        self.assertEqual(data["condition_b_masked"]["agreement_with_a_count"], 23)
        self.assertEqual(data["condition_b_masked"]["prediction_changes_count"], 5)


if __name__ == "__main__":
    unittest.main()

