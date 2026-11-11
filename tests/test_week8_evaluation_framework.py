"""
Automated Isolated Unit Tests for AgriMind Week 8:
Vision Evaluation Framework (Framework Validation Only — NOT PlantDoc Results).
Verifies label mapping, image integrity checks, metric calculations,
unreadable/unsupported sample handling, and reproducible artifact generation.
"""
import os
import sys
import json
import csv
import tempfile
import unittest
from typing import Dict, Any

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.vision.evaluation_framework import (
    LabelMapper,
    ImageIntegrityChecker,
    MetricCalculator,
    VisionDatasetEvaluator,
    CANONICAL_CLASSES
)


class TestWeek8EvaluationFramework(unittest.TestCase):
    """
    Test suite for Week 8 Evaluation Framework.
    All tests use synthetic or isolated fixtures; no external or restricted datasets accessed.
    """

    def test_01_label_mapper_canonical_and_plantdoc_aliases(self):
        """Verify LabelMapper translates canonical labels, PlantDoc directory names, and short names."""
        mapper = LabelMapper()

        # Canonical PlantVillage labels
        self.assertEqual(mapper.map_label("Tomato___Bacterial_spot"), "Tomato___Bacterial_spot")
        self.assertEqual(mapper.map_label("Tomato___Early_blight"), "Tomato___Early_blight")
        self.assertEqual(mapper.map_label("Tomato___Late_blight"), "Tomato___Late_blight")

        # Native PlantDoc folder names
        self.assertEqual(mapper.map_label("Tomato leaf bacterial spot"), "Tomato___Bacterial_spot")
        self.assertEqual(mapper.map_label("Tomato Early blight leaf"), "Tomato___Early_blight")
        self.assertEqual(mapper.map_label("Tomato leaf late blight"), "Tomato___Late_blight")

        # Normalized short names
        self.assertEqual(mapper.map_label("bacterial_spot"), "Tomato___Bacterial_spot")
        self.assertEqual(mapper.map_label("Early_blight"), "Tomato___Early_blight")
        self.assertEqual(mapper.map_label("late_blight"), "Tomato___Late_blight")

        # Support query
        self.assertTrue(mapper.is_supported("Tomato leaf late blight"))

    def test_02_label_mapper_unsupported_classes(self):
        """Verify unsupported or out-of-scope classes return None and are rejected cleanly."""
        mapper = LabelMapper()

        out_of_scope = [
            "Tomato leaf curl virus",
            "Tomato septoria leaf spot",
            "Apple rust leaf",
            "Corn common rust",
            "Pepper bell bacterial spot",
            "Tomato healthy",
            "",
            None
        ]

        for raw in out_of_scope:
            self.assertIsNone(mapper.map_label(raw))
            self.assertFalse(mapper.is_supported(raw))

    def test_03_image_integrity_checker(self):
        """Verify ImageIntegrityChecker identifies valid headers, missing files, and 0-byte corrupt files."""
        checker = ImageIntegrityChecker()

        # 1. Non-existent file
        res = checker.check_image("/path/to/nonexistent_image_12345.jpg")
        self.assertFalse(res["is_valid"])
        self.assertIn("not found", res["error"])

        # 2. Empty 0-byte file
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            temp_empty = f.name
        try:
            res_empty = checker.check_image(temp_empty)
            self.assertFalse(res_empty["is_valid"])
            self.assertIn("empty (0 bytes)", res_empty["error"])
        finally:
            if os.path.exists(temp_empty):
                os.remove(temp_empty)

        # 3. Valid JPEG header fixture
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")
            temp_jpeg = f.name
        try:
            res_jpeg = checker.check_image(temp_jpeg)
            self.assertTrue(res_jpeg["is_valid"])
            self.assertEqual(res_jpeg["detected_format"], "jpeg")
            self.assertGreater(res_jpeg["file_size_bytes"], 0)
        finally:
            if os.path.exists(temp_jpeg):
                os.remove(temp_jpeg)

        # 4. Corrupt non-image header
        with tempfile.NamedTemporaryFile("wb", delete=False) as f:
            f.write(b"NOT_AN_IMAGE_FILE_DATA")
            temp_corrupt = f.name
        try:
            res_corrupt = checker.check_image(temp_corrupt)
            self.assertFalse(res_corrupt["is_valid"])
            self.assertIn("Unrecognized image header", res_corrupt["error"])
        finally:
            if os.path.exists(temp_corrupt):
                os.remove(temp_corrupt)

    def test_04_metric_calculator_perfect_classification(self):
        """Verify metric calculation under 100% agreement."""
        gt = [
            "Tomato___Bacterial_spot", "Tomato___Bacterial_spot",
            "Tomato___Early_blight", "Tomato___Early_blight",
            "Tomato___Late_blight", "Tomato___Late_blight"
        ]
        pred = list(gt)

        metrics = MetricCalculator.compute_metrics(gt, pred)

        self.assertEqual(metrics["total_samples"], 6)
        self.assertEqual(metrics["accuracy"], 1.0)
        self.assertEqual(metrics["macro_f1"], 1.0)
        self.assertEqual(metrics["weighted_f1"], 1.0)
        self.assertEqual(metrics["missing_classes"], [])

        # Check per-class support and F1
        for short in ["Bacterial_spot", "Early_blight", "Late_blight"]:
            self.assertEqual(metrics["per_class"][short]["support"], 2)
            self.assertEqual(metrics["per_class"][short]["f1_score"], 1.0)

        # Confusion matrix must be diagonal [[2, 0, 0], [0, 2, 0], [0, 0, 2]]
        self.assertEqual(metrics["confusion_matrix"], [[2, 0, 0], [0, 2, 0], [0, 0, 2]])

    def test_05_metric_calculator_known_confusion(self):
        """
        Verify metric calculation with known misclassifications:
        3 Bacterial Spot (2 predicted BS, 1 predicted EB) -> Recall = 2/3 = 0.6667
        3 Early Blight   (3 predicted EB)                 -> Recall = 3/3 = 1.0000
        3 Late Blight    (2 predicted LB, 1 predicted EB) -> Recall = 2/3 = 0.6667
        """
        gt = [
            "Tomato___Bacterial_spot", "Tomato___Bacterial_spot", "Tomato___Bacterial_spot",
            "Tomato___Early_blight", "Tomato___Early_blight", "Tomato___Early_blight",
            "Tomato___Late_blight", "Tomato___Late_blight", "Tomato___Late_blight"
        ]
        pred = [
            "Tomato___Bacterial_spot", "Tomato___Bacterial_spot", "Tomato___Early_blight",
            "Tomato___Early_blight", "Tomato___Early_blight", "Tomato___Early_blight",
            "Tomato___Late_blight", "Tomato___Late_blight", "Tomato___Early_blight"
        ]

        metrics = MetricCalculator.compute_metrics(gt, pred)

        self.assertEqual(metrics["total_samples"], 9)
        # Correct = 2 + 3 + 2 = 7 -> Accuracy = 7/9 = 0.7778
        self.assertAlmostEqual(metrics["accuracy"], 0.7778, places=4)

        bs = metrics["per_class"]["Bacterial_spot"]
        eb = metrics["per_class"]["Early_blight"]
        lb = metrics["per_class"]["Late_blight"]

        self.assertAlmostEqual(bs["recall"], 0.6667, places=4)
        self.assertAlmostEqual(bs["precision"], 1.0000, places=4)  # 2 predicted BS, both true BS

        self.assertAlmostEqual(eb["recall"], 1.0000, places=4)     # All 3 true EB found
        self.assertAlmostEqual(eb["precision"], 3 / 5, places=4)   # 5 predicted EB (3 true EB, 1 BS, 1 LB)

        self.assertAlmostEqual(lb["recall"], 0.6667, places=4)
        self.assertAlmostEqual(lb["precision"], 1.0000, places=4)

        # Confusion matrix checks
        # Row 0 (BS): [2, 1, 0]
        # Row 1 (EB): [0, 3, 0]
        # Row 2 (LB): [0, 1, 2]
        expected_cm = [
            [2, 1, 0],
            [0, 3, 0],
            [0, 1, 2]
        ]
        self.assertEqual(metrics["confusion_matrix"], expected_cm)

    def test_06_metric_calculator_missing_classes(self):
        """Verify MetricCalculator reports missing classes when support == 0 without crashing."""
        gt = ["Tomato___Bacterial_spot", "Tomato___Early_blight"]
        pred = ["Tomato___Bacterial_spot", "Tomato___Early_blight"]

        metrics = MetricCalculator.compute_metrics(gt, pred)

        self.assertEqual(metrics["total_samples"], 2)
        self.assertIn("Tomato___Late_blight", metrics["missing_classes"])
        self.assertEqual(metrics["per_class"]["Late_blight"]["support"], 0)

    def test_07_evaluator_with_mock_model_clean_run(self):
        """
        Verify VisionDatasetEvaluator end-to-end with a deterministic mock model.
        """
        # Create 3 valid JPEG fixtures
        fixtures = []
        for i, cls_name in enumerate(CANONICAL_CLASSES):
            f = tempfile.NamedTemporaryFile("wb", suffix=".jpg", delete=False)
            f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")
            f.close()
            fixtures.append({"filepath": f.name, "label": cls_name})

        # Mock model function predicting perfectly
        def mock_perfect_infer(path: str) -> Dict[str, Any]:
            for item in fixtures:
                if item["filepath"] == path:
                    return {
                        "predicted_class": item["label"],
                        "confidence": 0.98,
                        "class_probabilities": {item["label"]: 0.98}
                    }
            return {"predicted_class": "Tomato___Early_blight", "confidence": 0.50}

        try:
            evaluator = VisionDatasetEvaluator(inference_fn=mock_perfect_infer)
            results = evaluator.evaluate_samples(
                samples=fixtures,
                benchmark_name="Synthetic-Validation-Test",
                is_synthetic=True
            )

            self.assertTrue(results["is_framework_validation"])
            self.assertEqual(results["summary"]["total_input_samples"], 3)
            self.assertEqual(results["summary"]["evaluated_samples"], 3)
            self.assertEqual(results["summary"]["unreadable_samples"], 0)
            self.assertEqual(results["summary"]["unsupported_samples"], 0)
            self.assertEqual(results["metrics"]["accuracy"], 1.0)
            self.assertEqual(len(results["sample_results"]), 3)

            # Verify separation of fields in sample results
            sample0 = results["sample_results"][0]
            self.assertIn("sample_id", sample0)
            self.assertIn("filepath", sample0)
            self.assertIn("ground_truth_raw", sample0)
            self.assertIn("ground_truth_mapped", sample0)
            self.assertIn("predicted_class", sample0)
            self.assertTrue(sample0["is_correct"])

        finally:
            for item in fixtures:
                if os.path.exists(item["filepath"]):
                    os.remove(item["filepath"])

    def test_08_evaluator_unreadable_and_unsupported_handling(self):
        """
        Verify evaluator gracefully catalogs corrupt files and unsupported classes
        without failing the evaluation run.
        """
        # 1. Valid file
        f_valid = tempfile.NamedTemporaryFile("wb", suffix=".jpg", delete=False)
        f_valid.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00")
        f_valid.close()

        # 2. Corrupt file (0 bytes)
        f_corrupt = tempfile.NamedTemporaryFile("wb", suffix=".jpg", delete=False)
        f_corrupt.close()

        samples = [
            {"filepath": f_valid.name, "label": "Tomato leaf bacterial spot"},           # Valid PlantDoc alias
            {"filepath": f_corrupt.name, "label": "Tomato Early blight leaf"},           # Unreadable (0 bytes)
            {"filepath": "/missing/file.jpg", "label": "Tomato leaf late blight"},        # Missing file
            {"filepath": f_valid.name, "label": "Tomato leaf curl virus"}                 # Out of scope class
        ]

        def mock_infer(path: str) -> Dict[str, Any]:
            return {"predicted_class": "Tomato___Bacterial_spot", "confidence": 0.95}

        try:
            evaluator = VisionDatasetEvaluator(inference_fn=mock_infer)
            results = evaluator.evaluate_samples(
                samples=samples,
                benchmark_name="Robustness-Test",
                is_synthetic=True
            )

            self.assertEqual(results["summary"]["total_input_samples"], 4)
            self.assertEqual(results["summary"]["evaluated_samples"], 1)
            self.assertEqual(results["summary"]["unreadable_samples"], 2)   # 1 corrupt + 1 missing
            self.assertEqual(results["summary"]["unsupported_samples"], 1)  # 1 out-of-scope leaf curl

            # Check unreadable list records
            self.assertEqual(len(results["unreadable_samples"]), 2)
            self.assertIn("empty (0 bytes)", results["unreadable_samples"][0]["error"])
            self.assertIn("not found", results["unreadable_samples"][1]["error"])

            # Check unsupported list records
            self.assertEqual(len(results["unsupported_samples"]), 1)
            self.assertEqual(results["unsupported_samples"][0]["raw_label"], "Tomato leaf curl virus")

        finally:
            if os.path.exists(f_valid.name):
                os.remove(f_valid.name)
            if os.path.exists(f_corrupt.name):
                os.remove(f_corrupt.name)

    def test_09_artifact_export_reproducibility(self):
        """
        Verify export_artifacts creates metrics.json, predictions.csv, and evaluation_report.md
        with transparent framework validation disclaimers.
        """
        payload = {
            "evaluation_id": "EVAL-TEST001",
            "benchmark_name": "Framework-Validation-Unit-Test",
            "timestamp": "2026-10-26T12:00:00Z",
            "is_framework_validation": True,
            "summary": {
                "total_input_samples": 2,
                "evaluated_samples": 2,
                "unreadable_samples": 0,
                "unsupported_samples": 0
            },
            "metrics": {
                "total_samples": 2,
                "accuracy": 1.0,
                "macro_precision": 1.0,
                "macro_recall": 1.0,
                "macro_f1": 1.0,
                "weighted_precision": 1.0,
                "weighted_recall": 1.0,
                "weighted_f1": 1.0,
                "per_class": {
                    "Bacterial_spot": {"precision": 1.0, "recall": 1.0, "f1_score": 1.0, "support": 1},
                    "Early_blight": {"precision": 1.0, "recall": 1.0, "f1_score": 1.0, "support": 1},
                    "Late_blight": {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "support": 0}
                },
                "confusion_matrix": [[1, 0, 0], [0, 1, 0], [0, 0, 0]],
                "class_order": ["Bacterial_spot", "Early_blight", "Late_blight"],
                "missing_classes": ["Tomato___Late_blight"]
            },
            "unreadable_samples": [],
            "unsupported_samples": [],
            "sample_results": [
                {
                    "sample_id": "SMPL-00001",
                    "filepath": "/test/path/img1.jpg",
                    "ground_truth_raw": "Tomato leaf bacterial spot",
                    "ground_truth_mapped": "Tomato___Bacterial_spot",
                    "predicted_class": "Tomato___Bacterial_spot",
                    "confidence": 0.99,
                    "is_correct": True
                },
                {
                    "sample_id": "SMPL-00002",
                    "filepath": "/test/path/img2.jpg",
                    "ground_truth_raw": "Tomato Early blight leaf",
                    "ground_truth_mapped": "Tomato___Early_blight",
                    "predicted_class": "Tomato___Early_blight",
                    "confidence": 0.95,
                    "is_correct": True
                }
            ]
        }

        with tempfile.TemporaryDirectory() as temp_out_dir:
            exported = VisionDatasetEvaluator.export_artifacts(payload, temp_out_dir)

            # 1. metrics.json exists and loads
            self.assertTrue(os.path.exists(exported["metrics_json"]))
            with open(exported["metrics_json"], "r") as f:
                saved_metrics = json.load(f)
            self.assertEqual(saved_metrics["metrics"]["accuracy"], 1.0)

            # 2. predictions.csv exists and has headers
            self.assertTrue(os.path.exists(exported["predictions_csv"]))
            with open(exported["predictions_csv"], "r") as f:
                reader = list(csv.reader(f))
            self.assertEqual(reader[0], [
                "sample_id", "filepath", "ground_truth_raw", "ground_truth_mapped",
                "predicted_class", "confidence", "is_correct"
            ])
            self.assertEqual(len(reader), 3)  # header + 2 samples

            # 3. evaluation_report.md exists and contains disclaimer
            self.assertTrue(os.path.exists(exported["evaluation_report"]))
            with open(exported["evaluation_report"], "r") as f:
                report_text = f.read()
            self.assertIn("FRAMEWORK VALIDATION RUN ONLY", report_text)
            self.assertIn("NOT a PlantDoc dataset evaluation", report_text)
            self.assertIn("Overall Accuracy", report_text)
            self.assertIn("Confusion Matrix", report_text)

    def test_10_evaluation_report_formatting(self):
        """Verify markdown report contains correctly formatted tables and headers."""
        payload = {
            "evaluation_id": "EVAL-FMT001",
            "benchmark_name": "Formatting-Check",
            "timestamp": "2026-10-26T12:00:00Z",
            "is_framework_validation": True,
            "summary": {"total_input_samples": 1, "evaluated_samples": 1, "unreadable_samples": 0, "unsupported_samples": 0},
            "metrics": {
                "accuracy": 0.85,
                "macro_precision": 0.85,
                "macro_recall": 0.85,
                "macro_f1": 0.85,
                "weighted_f1": 0.85,
                "per_class": {
                    "Bacterial_spot": {"precision": 0.85, "recall": 0.85, "f1_score": 0.85, "support": 10}
                },
                "confusion_matrix": [[10]],
                "class_order": ["Bacterial_spot"],
                "missing_classes": []
            },
            "unreadable_samples": [],
            "unsupported_samples": [],
            "sample_results": []
        }

        report = VisionDatasetEvaluator.generate_markdown_report(payload)
        self.assertIn("# AgriMind Vision Evaluation Report", report)
        self.assertIn("| Disease Class | Precision | Recall | F1-Score | Sample Support |", report)
        self.assertIn("| True \\ Predicted | **Pred: Bacterial_spot** |", report)

    def test_11_undefined_precision_zero_division_notice(self):
        """Verify metric calculation and report handling when a class has zero predicted samples."""
        gt = [
            "Tomato___Bacterial_spot", "Tomato___Bacterial_spot",
            "Tomato___Early_blight", "Tomato___Early_blight"
        ]
        # Model predicts Early Blight for all 4 samples (zero Bacterial Spot predictions)
        pred = [
            "Tomato___Early_blight", "Tomato___Early_blight",
            "Tomato___Early_blight", "Tomato___Early_blight"
        ]

        metrics = MetricCalculator.compute_metrics(gt, pred)

        # Bacterial Spot has TP=0, FP=0 -> Precision is 0/0 -> zero_division=0 sets it to 0.0
        bs = metrics["per_class"]["Bacterial_spot"]
        self.assertEqual(bs["support"], 2)
        self.assertEqual(bs["precision"], 0.0)
        self.assertEqual(bs["recall"], 0.0)
        self.assertEqual(bs["f1_score"], 0.0)

        payload = {
            "evaluation_id": "EVAL-ZERO001",
            "benchmark_name": "Zero-Division-Test",
            "timestamp": "2026-10-26T12:00:00Z",
            "is_framework_validation": True,
            "summary": {"total_input_samples": 4, "evaluated_samples": 4, "unreadable_samples": 0, "unsupported_samples": 0},
            "metrics": metrics,
            "unreadable_samples": [],
            "unsupported_samples": [],
            "sample_results": []
        }

        report = VisionDatasetEvaluator.generate_markdown_report(payload)
        self.assertIn("Zero Predicted Samples / Undefined Precision", report)
        self.assertIn("zero_division=0", report)


if __name__ == "__main__":
    unittest.main()

