"""
Unit tests for AgriMind Week 8 Evaluation Corrections and Preprocessing Experiment.
Validates:
1. Dynamic loading of authoritative PlantVillage baseline and error handling.
2. Terminology compliance.
3. Preprocessing transforms output shape (3, 224, 224) across diverse image aspect ratios.
4. Strict sample alignment and artifact integrity.
"""
import os
import sys
import json
import tempfile
import unittest
import numpy as np
from PIL import Image
import torch

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from scripts.run_plantdoc_evaluation import (
    load_authoritative_plantvillage_baseline,
)
from scripts.run_preprocessing_experiment import (
    transform_baseline,
    transform_padding,
    transform_direct_resize,
    OUTPUT_EXP_DIR,
    PV_BASELINE_JSON
)


class TestAuthoritativeBaselineLoader(unittest.TestCase):
    """Tests dynamic baseline loading and error handling."""

    def test_load_authoritative_baseline_valid(self):
        """Authoritative PlantVillage baseline artifact loads with correct metrics."""
        self.assertTrue(os.path.exists(PV_BASELINE_JSON), f"Baseline missing: {PV_BASELINE_JSON}")
        baseline = load_authoritative_plantvillage_baseline(PV_BASELINE_JSON)

        self.assertAlmostEqual(baseline["accuracy"], 0.9841, places=4)
        self.assertAlmostEqual(baseline["macro_f1"], 0.9828, places=4)
        self.assertAlmostEqual(baseline["weighted_f1"], 0.9841, places=4)
        self.assertAlmostEqual(baseline["macro_precision"], 0.9858, places=4)
        self.assertAlmostEqual(baseline["macro_recall"], 0.9799, places=4)
        self.assertEqual(baseline["total_samples"], 1007)
        self.assertEqual(baseline["correct_samples"], 991)
        self.assertIn("per_class", baseline)
        self.assertIn("confusion_matrix", baseline)

    def test_load_authoritative_baseline_missing_file(self):
        """Missing baseline file raises FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            load_authoritative_plantvillage_baseline("/path/does/not/exist/baseline.json")

    def test_load_authoritative_baseline_invalid_json(self):
        """Malformed JSON raises ValueError."""
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{ invalid json")
            tmp_path = f.name
        try:
            with self.assertRaises(ValueError):
                load_authoritative_plantvillage_baseline(tmp_path)
        finally:
            os.remove(tmp_path)

    def test_load_authoritative_baseline_missing_keys(self):
        """JSON missing required top-level keys raises KeyError."""
        incomplete_data = {"accuracy": 0.95}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(incomplete_data, f)
            tmp_path = f.name
        try:
            with self.assertRaises(KeyError):
                load_authoritative_plantvillage_baseline(tmp_path)
        finally:
            os.remove(tmp_path)


class TestPreprocessingTransforms(unittest.TestCase):
    """Tests tensor shapes and behavior for the 3 preprocessing pipelines."""

    def test_transform_output_shapes(self):
        """All three transforms must produce tensors of shape (3, 224, 224)."""
        test_resolutions = [
            (224, 224),   # square
            (500, 300),   # landscape
            (300, 700),   # portrait
            (1024, 1024), # large square
            (150, 150)    # small square
        ]

        for w, h in test_resolutions:
            img = Image.new("RGB", (w, h), color=(128, 64, 32))

            t_base = transform_baseline(img)
            self.assertEqual(t_base.shape, torch.Size([3, 224, 224]))
            self.assertEqual(t_base.dtype, torch.float32)

            t_pad = transform_padding(img)
            self.assertEqual(t_pad.shape, torch.Size([3, 224, 224]))
            self.assertEqual(t_pad.dtype, torch.float32)

            t_direct = transform_direct_resize(img)
            self.assertEqual(t_direct.shape, torch.Size([3, 224, 224]))
            self.assertEqual(t_direct.dtype, torch.float32)

    def test_padding_centering(self):
        """Tests that padding centers a landscape image horizontally/vertically."""
        # Landscape image: 200 wide by 100 high
        # Longer edge 224 -> new_w = 224, new_h = round(100 * 224 / 200) = 112
        # Vertical padding should be (224 - 112) // 2 = 56 top and bottom
        img = Image.new("RGB", (200, 100), color=(255, 255, 255))
        tensor = transform_padding(img)
        self.assertEqual(tensor.shape, torch.Size([3, 224, 224]))


class TestExperimentArtifacts(unittest.TestCase):
    """Tests integrity of exported preprocessing experiment artifacts."""

    def test_experiment_artifacts_exist(self):
        """All required experiment artifact files exist in outputs directory."""
        required_files = [
            "condition_1_baseline_metrics.json",
            "condition_2_padding_metrics.json",
            "condition_3_direct_resize_metrics.json",
            "comparative_metrics.json",
            "per_image_predictions.csv",
            "inference_timing.json",
            "experiment_summary.md",
            os.path.join("confusion_matrices", "confusion_matrix_condition_1.json"),
            os.path.join("confusion_matrices", "confusion_matrix_condition_2.json"),
            os.path.join("confusion_matrices", "confusion_matrix_condition_3.json"),
        ]

        for fname in required_files:
            fpath = os.path.join(OUTPUT_EXP_DIR, fname)
            self.assertTrue(os.path.exists(fpath), f"Required artifact missing: {fpath}")

    def test_predictions_csv_alignment(self):
        """Predictions CSV has exactly 28 rows, all required columns, and valid ground truths."""
        csv_path = os.path.join(OUTPUT_EXP_DIR, "per_image_predictions.csv")
        with open(csv_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        # 1 header + 28 data rows = 29 lines
        self.assertEqual(len(lines), 29)
        header = lines[0].split(",")
        required_cols = [
            "sample_id", "filepath", "filename", "ground_truth",
            "cond1_pred", "cond1_conf", "cond1_correct",
            "cond2_pred", "cond2_conf", "cond2_correct",
            "cond3_pred", "cond3_conf", "cond3_correct",
            "all_agree"
        ]
        for col in required_cols:
            self.assertIn(col, header)

    def test_comparative_metrics_consistency(self):
        """Comparative metrics JSON contains consistent sample counts and values."""
        comp_path = os.path.join(OUTPUT_EXP_DIR, "comparative_metrics.json")
        with open(comp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("baseline_plantvillage", data)
        self.assertIn("condition_1_baseline_crop", data)
        self.assertIn("condition_2_aspect_padding", data)
        self.assertIn("condition_3_direct_squash", data)

        c1 = data["condition_1_baseline_crop"]
        c2 = data["condition_2_aspect_padding"]
        c3 = data["condition_3_direct_squash"]

        self.assertAlmostEqual(c1["accuracy"], 0.3929, places=4)
        self.assertAlmostEqual(c2["accuracy"], 0.4286, places=4)
        self.assertAlmostEqual(c3["accuracy"], 0.5357, places=4)

        # Bacterial spot recall must be 0.0 in all conditions
        self.assertEqual(c1["per_class"]["Bacterial_spot"]["recall"], 0.0)
        self.assertEqual(c2["per_class"]["Bacterial_spot"]["recall"], 0.0)
        self.assertEqual(c3["per_class"]["Bacterial_spot"]["recall"], 0.0)


if __name__ == "__main__":
    unittest.main()

