"""
AgriMind Vision Evaluation Framework (Week 8 Preparation).
Provides a comprehensive, safe, and reproducible evaluation suite for benchmarking
the 3-class Tomato crop disease baseline on external datasets.

Features:
- Standardized label mapping and unmapped/unsupported class detection.
- Pre-execution image file integrity and readability checks.
- Transparent separation of ground-truth labels, model predictions, and metrics.
- Comprehensive metric calculations: Accuracy, Macro-F1, Weighted-F1, per-class P/R/F1,
  confusion matrix, and missing-class reporting.
- Reproducible export artifacts: metrics.json, predictions.csv, and evaluation_report.md.
"""
import os
import csv
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Union, Callable
import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score

# Canonical 3-class scope defined in Weeks 1-2
CANONICAL_CLASSES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight"
]

CANONICAL_SHORT_NAMES = [
    "Bacterial_spot",
    "Early_blight",
    "Late_blight"
]

# Standard aliases across datasets (PlantVillage, PlantDoc directory names, short names)
DEFAULT_LABEL_MAPPINGS: Dict[str, str] = {
    # PlantVillage canonical format
    "Tomato___Bacterial_spot": "Tomato___Bacterial_spot",
    "Tomato___Early_blight": "Tomato___Early_blight",
    "Tomato___Late_blight": "Tomato___Late_blight",
    # PlantDoc native directory names
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato leaf late blight": "Tomato___Late_blight",
    # Normalized short names
    "Bacterial_spot": "Tomato___Bacterial_spot",
    "Early_blight": "Tomato___Early_blight",
    "Late_blight": "Tomato___Late_blight",
    "bacterial_spot": "Tomato___Bacterial_spot",
    "early_blight": "Tomato___Early_blight",
    "late_blight": "Tomato___Late_blight",
}


class LabelMapper:
    """
    Manages translation of heterogeneous dataset labels into AgriMind canonical classes.
    Explicitly flags unmapped, out-of-scope, or corrupted class labels.
    """

    def __init__(
        self,
        target_classes: Optional[List[str]] = None,
        custom_mappings: Optional[Dict[str, str]] = None
    ):
        self.target_classes = target_classes or list(CANONICAL_CLASSES)
        self.mappings = dict(DEFAULT_LABEL_MAPPINGS)
        if custom_mappings:
            self.mappings.update(custom_mappings)

    def map_label(self, raw_label: str) -> Optional[str]:
        """
        Maps a raw label string to a canonical target class.
        Returns None if the label is unrecognized or outside model scope.
        """
        if not raw_label or not isinstance(raw_label, str):
            return None
        
        clean = raw_label.strip()
        # Direct lookup
        if clean in self.mappings:
            return self.mappings[clean]
        
        # Lowercase / trimmed normalization lookup
        clean_lower = clean.lower().replace(" ", "_").replace("-", "_")
        for k, v in self.mappings.items():
            k_norm = k.lower().replace(" ", "_").replace("-", "_")
            if clean_lower == k_norm:
                return v

        return None

    def is_supported(self, raw_label: str) -> bool:
        """Returns True if the raw label successfully maps to a target class."""
        mapped = self.map_label(raw_label)
        return mapped in self.target_classes


class ImageIntegrityChecker:
    """
    Validates physical image file accessibility and header integrity before inference.
    Prevents corrupt files from crashing batch evaluation pipelines.
    """

    SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}

    @classmethod
    def check_image(cls, image_path: str) -> Dict[str, Any]:
        """
        Inspects image file existence, non-zero size, and header magic bytes.
        """
        if not image_path or not isinstance(image_path, str) or not image_path.strip():
            return {
                "is_valid": False,
                "error": "Empty or non-string file path provided.",
                "file_size_bytes": 0,
                "detected_format": None
            }

        clean_path = image_path.strip()
        if not os.path.exists(clean_path):
            return {
                "is_valid": False,
                "error": f"Image file not found at: {clean_path}",
                "file_size_bytes": 0,
                "detected_format": None
            }

        try:
            file_size = os.path.getsize(clean_path)
            if file_size == 0:
                return {
                    "is_valid": False,
                    "error": f"File is empty (0 bytes): {clean_path}",
                    "file_size_bytes": 0,
                    "detected_format": None
                }

            with open(clean_path, "rb") as f:
                header = f.read(16)

            if header.startswith(b"\xff\xd8"):
                fmt = "jpeg"
            elif header.startswith(b"\x89PNG\r\n\x1a\n"):
                fmt = "png"
            elif header.startswith(b"GIF87a") or header.startswith(b"GIF89a"):
                fmt = "gif"
            elif header.startswith(b"BM"):
                fmt = "bmp"
            elif header.startswith(b"RIFF") and b"WEBP" in header:
                fmt = "webp"
            else:
                return {
                    "is_valid": False,
                    "error": f"Unrecognized image header magic bytes at: {clean_path}",
                    "file_size_bytes": file_size,
                    "detected_format": "unknown"
                }

            return {
                "is_valid": True,
                "error": None,
                "file_size_bytes": file_size,
                "detected_format": fmt
            }

        except Exception as e:
            return {
                "is_valid": False,
                "error": f"I/O error while reading image: {str(e)}",
                "file_size_bytes": 0,
                "detected_format": None
            }


class MetricCalculator:
    """
    Computes rigorous multi-class classification metrics:
    Accuracy, Macro-F1, Weighted-F1, per-class Precision/Recall/F1/Support,
    confusion matrix, and missing-class diagnostics.
    """

    @classmethod
    def compute_metrics(
        cls,
        ground_truth: List[str],
        predictions: List[str],
        target_classes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Computes formal classification metrics across aligned ground-truth and prediction vectors.
        """
        classes = target_classes or list(CANONICAL_CLASSES)
        class_to_idx = {c: i for i, c in enumerate(classes)}

        if len(ground_truth) != len(predictions):
            raise ValueError(
                f"Length mismatch: {len(ground_truth)} ground-truth labels vs {len(predictions)} predictions."
            )

        total_samples = len(ground_truth)
        if total_samples == 0:
            return {
                "total_samples": 0,
                "accuracy": 0.0,
                "macro_precision": 0.0,
                "macro_recall": 0.0,
                "macro_f1": 0.0,
                "weighted_precision": 0.0,
                "weighted_recall": 0.0,
                "weighted_f1": 0.0,
                "per_class": {c: {"precision": 0.0, "recall": 0.0, "f1_score": 0.0, "support": 0} for c in classes},
                "confusion_matrix": [[0 for _ in classes] for _ in classes],
                "class_order": classes,
                "missing_classes": list(classes)
            }

        # Convert strings to numeric indices
        y_true = np.array([class_to_idx[gt] for gt in ground_truth], dtype=int)
        y_pred = np.array([class_to_idx[pr] for pr in predictions], dtype=int)
        all_labels = list(range(len(classes)))

        # Overall accuracy
        acc = float(accuracy_score(y_true, y_pred))

        # Per-class metrics
        prec, rec, f1, sup = precision_recall_fscore_support(
            y_true, y_pred, labels=all_labels, zero_division=0
        )

        # Macro averages
        macro_p = float(np.mean(prec))
        macro_r = float(np.mean(rec))
        macro_f1 = float(np.mean(f1))

        # Weighted averages
        w_p, w_r, w_f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average="weighted", zero_division=0
        )

        # Confusion Matrix
        cm = confusion_matrix(y_true, y_pred, labels=all_labels)

        # Missing classes in evaluation set (support == 0)
        missing_classes = [classes[i] for i, s in enumerate(sup) if s == 0]

        per_class_dict = {}
        for i, c_name in enumerate(classes):
            short = c_name.replace("Tomato___", "")
            per_class_dict[short] = {
                "canonical_name": c_name,
                "precision": round(float(prec[i]), 4),
                "recall": round(float(rec[i]), 4),
                "f1_score": round(float(f1[i]), 4),
                "support": int(sup[i])
            }

        return {
            "total_samples": total_samples,
            "accuracy": round(acc, 4),
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4),
            "weighted_precision": round(float(w_p), 4),
            "weighted_recall": round(float(w_r), 4),
            "weighted_f1": round(float(w_f1), 4),
            "per_class": per_class_dict,
            "confusion_matrix": cm.tolist(),
            "class_order": [c.replace("Tomato___", "") for c in classes],
            "canonical_class_order": classes,
            "missing_classes": missing_classes
        }


class VisionDatasetEvaluator:
    """
    End-to-end evaluation harness for crop disease vision classifiers.
    Performs manifest validation, image integrity checking, model inference,
    metric calculation, and reproducible artifact export.
    """

    def __init__(
        self,
        inference_fn: Optional[Callable[[str], Dict[str, Any]]] = None,
        label_mapper: Optional[LabelMapper] = None,
        target_classes: Optional[List[str]] = None
    ):
        self.label_mapper = label_mapper or LabelMapper(target_classes=target_classes)
        self.target_classes = target_classes or list(CANONICAL_CLASSES)
        self._inference_fn = inference_fn

    def _default_inference(self, image_path: str) -> Dict[str, Any]:
        """Uses default local ResNet-50 VisionInferenceEngine if no custom fn is provided."""
        from src.vision.inference import VisionInferenceEngine
        engine = VisionInferenceEngine()
        pred = engine.predict(image_path)
        return {
            "predicted_class": pred.predicted_class,
            "confidence": pred.confidence,
            "class_probabilities": pred.class_probabilities
        }

    def evaluate_samples(
        self,
        samples: List[Dict[str, str]],
        benchmark_name: str = "Evaluation Benchmark",
        is_synthetic: bool = False
    ) -> Dict[str, Any]:
        """
        Evaluates a list of sample dictionaries:
        Each item must have: {"filepath": str, "label": str}
        """
        inference_func = self._inference_fn or self._default_inference

        valid_ground_truth = []
        valid_predictions = []
        sample_results = []
        unreadable_samples = []
        unsupported_samples = []

        for idx, item in enumerate(samples, start=1):
            filepath = item.get("filepath", "")
            raw_label = item.get("label", "")
            sample_id = f"SMPL-{idx:05d}"

            # Step 1: Label Mapping
            mapped_label = self.label_mapper.map_label(raw_label)
            if mapped_label is None or mapped_label not in self.target_classes:
                unsupported_samples.append({
                    "sample_id": sample_id,
                    "filepath": filepath,
                    "raw_label": raw_label,
                    "reason": "Out of scope or unmapped disease class"
                })
                continue

            # Step 2: Image Integrity Check
            check = ImageIntegrityChecker.check_image(filepath)
            if not check["is_valid"]:
                unreadable_samples.append({
                    "sample_id": sample_id,
                    "filepath": filepath,
                    "raw_label": raw_label,
                    "mapped_label": mapped_label,
                    "error": check["error"]
                })
                continue

            # Step 3: Inference
            try:
                pred_dict = inference_func(filepath)
                predicted_class = pred_dict.get("predicted_class")
                confidence = float(pred_dict.get("confidence", 0.0))
                class_probs = pred_dict.get("class_probabilities", {})

                is_correct = (predicted_class == mapped_label)
                valid_ground_truth.append(mapped_label)
                valid_predictions.append(predicted_class)

                sample_results.append({
                    "sample_id": sample_id,
                    "filepath": filepath,
                    "ground_truth_raw": raw_label,
                    "ground_truth_mapped": mapped_label,
                    "predicted_class": predicted_class,
                    "confidence": round(confidence, 4),
                    "is_correct": is_correct,
                    "class_probabilities": class_probs
                })

            except Exception as e:
                unreadable_samples.append({
                    "sample_id": sample_id,
                    "filepath": filepath,
                    "raw_label": raw_label,
                    "mapped_label": mapped_label,
                    "error": f"Inference execution failed: {str(e)}"
                })

        # Step 4: Metric Calculation
        metrics = MetricCalculator.compute_metrics(
            ground_truth=valid_ground_truth,
            predictions=valid_predictions,
            target_classes=self.target_classes
        )

        evaluation_payload = {
            "evaluation_id": f"EVAL-{uuid.uuid4().hex[:8].upper()}",
            "benchmark_name": benchmark_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "is_framework_validation": is_synthetic,
            "summary": {
                "total_input_samples": len(samples),
                "evaluated_samples": len(valid_ground_truth),
                "unreadable_samples": len(unreadable_samples),
                "unsupported_samples": len(unsupported_samples)
            },
            "metrics": metrics,
            "unreadable_samples": unreadable_samples,
            "unsupported_samples": unsupported_samples,
            "sample_results": sample_results
        }

        return evaluation_payload

    @classmethod
    def export_artifacts(
        cls,
        evaluation_payload: Dict[str, Any],
        output_dir: str
    ) -> Dict[str, str]:
        """
        Exports metrics.json, predictions.csv, and evaluation_report.md into output_dir.
        """
        os.makedirs(output_dir, exist_ok=True)
        paths = {}

        # 1. metrics.json (excluding individual sample arrays to keep clean summary)
        metrics_summary = {k: v for k, v in evaluation_payload.items() if k != "sample_results"}
        metrics_json_path = os.path.join(output_dir, "metrics.json")
        with open(metrics_json_path, "w", encoding="utf-8") as f:
            json.dump(metrics_summary, f, indent=2)
        paths["metrics_json"] = metrics_json_path

        # 2. predictions.csv
        predictions_csv_path = os.path.join(output_dir, "predictions.csv")
        sample_results = evaluation_payload.get("sample_results", [])
        fieldnames = [
            "sample_id", "filepath", "ground_truth_raw", "ground_truth_mapped",
            "predicted_class", "confidence", "is_correct"
        ]
        with open(predictions_csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for smpl in sample_results:
                writer.writerow(smpl)
        paths["predictions_csv"] = predictions_csv_path

        # 3. evaluation_report.md
        report_md_path = os.path.join(output_dir, "evaluation_report.md")
        report_content = cls.generate_markdown_report(evaluation_payload)
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        paths["evaluation_report"] = report_md_path

        return paths

    @classmethod
    def generate_markdown_report(cls, payload: Dict[str, Any]) -> str:
        """
        Builds a human-readable, student-friendly Markdown evaluation report.
        """
        bench_name = payload.get("benchmark_name", "Evaluation Benchmark")
        is_synthetic = payload.get("is_framework_validation", False)
        summary = payload.get("summary", {})
        metrics = payload.get("metrics", {})
        per_class = metrics.get("per_class", {})
        cm = metrics.get("confusion_matrix", [])
        order = metrics.get("class_order", [])

        lines = []
        lines.append(f"# AgriMind Vision Evaluation Report — {bench_name}")
        lines.append("")
        if is_synthetic:
            lines.append("> [!NOTE]")
            lines.append("> **FRAMEWORK VALIDATION RUN ONLY:** This report reflects synthetic/mock test fixtures executed")
            lines.append("> to verify the evaluation pipeline. **This is NOT a PlantDoc dataset evaluation.**")
            lines.append("> Real PlantDoc evaluation remains pending until an authorized dataset path is explicitly provided.")
            lines.append("")

        lines.append(f"- **Evaluation ID:** `{payload.get('evaluation_id')}`")
        lines.append(f"- **Timestamp:** `{payload.get('timestamp')}`")
        lines.append(f"- **Total Input Samples:** `{summary.get('total_input_samples', 0)}`")
        lines.append(f"- **Successfully Evaluated:** `{summary.get('evaluated_samples', 0)}`")
        lines.append(f"- **Unreadable / Corrupt Images:** `{summary.get('unreadable_samples', 0)}`")
        lines.append(f"- **Unsupported / Out-of-Scope Classes:** `{summary.get('unsupported_samples', 0)}`")
        lines.append("")

        lines.append("## 1. Overall Performance Summary")
        lines.append("")
        lines.append("| Metric | Score | Description |")
        lines.append("| :--- | :---: | :--- |")
        lines.append(f"| **Overall Accuracy** | `{metrics.get('accuracy', 0.0):.4f}` | Proportion of correctly classified leaves |")
        lines.append(f"| **Macro Precision** | `{metrics.get('macro_precision', 0.0):.4f}` | Unweighted mean precision across classes |")
        lines.append(f"| **Macro Recall** | `{metrics.get('macro_recall', 0.0):.4f}` | Unweighted mean recall across classes |")
        lines.append(f"| **Macro F1-Score** | `{metrics.get('macro_f1', 0.0):.4f}` | Primary metric accounting for class imbalance |")
        lines.append(f"| **Weighted F1-Score** | `{metrics.get('weighted_f1', 0.0):.4f}` | Support-weighted mean F1-score |")
        lines.append("")

        lines.append("## 2. Per-Class Diagnostic Performance")
        lines.append("")
        lines.append("| Disease Class | Precision | Recall | F1-Score | Sample Support |")
        lines.append("| :--- | :---: | :---: | :---: | :---: |")
        for c_short, c_data in per_class.items():
            lines.append(
                f"| **{c_short}** | `{c_data.get('precision', 0.0):.4f}` | `{c_data.get('recall', 0.0):.4f}` | `{c_data.get('f1_score', 0.0):.4f}` | `{c_data.get('support', 0)}` |"
            )
        lines.append("")

        if metrics.get("missing_classes"):
            lines.append("> [!WARNING]")
            lines.append(f"> **Missing Evaluation Classes:** The dataset contained zero samples for: {', '.join(metrics.get('missing_classes'))}.")
            lines.append("")

        # Check for classes with zero predicted samples where support > 0
        zero_pred_classes = [
            c_short for c_short, c_data in per_class.items()
            if c_data.get("precision", 0.0) == 0.0 and c_data.get("recall", 0.0) == 0.0 and c_data.get("support", 0) > 0
        ]
        if zero_pred_classes:
            lines.append("> [!NOTE]")
            lines.append(
                f"> **Zero Predicted Samples / Undefined Precision:** The model predicted zero samples for {', '.join(zero_pred_classes)}. "
                "Precision is mathematically undefined (0/0) and set to 0.0000 per the zero_division=0 standard."
            )
            lines.append("")

        lines.append("## 3. Confusion Matrix")
        lines.append("")
        if cm and order:
            header_str = " | ".join([f"**Pred: {c}**" for c in order])
            lines.append(f"| True \\ Predicted | {header_str} |")
            lines.append("| :--- | " + " | ".join([":---:" for _ in order]) + " |")
            for i, true_class in enumerate(order):
                row_str = " | ".join([str(cm[i][j]) for j in range(len(order))])
                lines.append(f"| **True: {true_class}** | {row_str} |")
            lines.append("")

        unreadable = payload.get("unreadable_samples", [])
        if unreadable:
            lines.append("## 4. Unreadable / Corrupted Image Audit")
            lines.append("")
            lines.append("| Sample ID | File Path | Error Encountered |")
            lines.append("| :--- | :--- | :--- |")
            for un in unreadable[:10]:
                lines.append(f"| `{un.get('sample_id')}` | `{un.get('filepath')}` | `{un.get('error')}` |")
            if len(unreadable) > 10:
                lines.append(f"| ... | *[{len(unreadable) - 10} additional unreadable files omitted]* | ... |")
            lines.append("")

        unsupported = payload.get("unsupported_samples", [])
        if unsupported:
            lines.append("## 5. Unsupported / Out-of-Scope Class Audit")
            lines.append("")
            lines.append("| Sample ID | File Path | Raw Label | Status |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for uns in unsupported[:10]:
                lines.append(f"| `{uns.get('sample_id')}` | `{uns.get('filepath')}` | `{uns.get('raw_label')}` | Out of Scope |")
            if len(unsupported) > 10:
                lines.append(f"| ... | *[{len(unsupported) - 10} additional unsupported files omitted]* | ... | ... |")
            lines.append("")

        return "\n".join(lines)
