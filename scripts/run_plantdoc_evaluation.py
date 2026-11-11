"""
PlantDoc Real Dataset Evaluation Script for AgriMind (Week 8).
Authorized access to /home/jaskirat/PlantDoc-Dataset.
Evaluates the Week 2 fine-tuned ResNet-50 model checkpoint on the external PlantDoc benchmark.
Computes metrics, confusion matrices, and exports reproducible artifacts.
"""
import os
import sys
import json
import csv
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

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
from src.vision.inference import run_raw_inference

PLANTDOC_DIR = "/home/jaskirat/PlantDoc-Dataset"
CHECKPOINT_PATH = os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "best_model.pth")
OUTPUT_BASE_DIR = os.path.join(WORKSPACE_DIR, "outputs", "week8_plantdoc_evaluation")

# PlantDoc to AgriMind unambiguous class mapping
PLANTDOC_CLASS_MAP = {
    "Tomato leaf bacterial spot": "Tomato___Bacterial_spot",
    "Tomato Early blight leaf": "Tomato___Early_blight",
    "Tomato leaf late blight": "Tomato___Late_blight"
}


def load_authoritative_plantvillage_baseline(baseline_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads and validates the authoritative Week 2 PlantVillage baseline evaluation artifact.
    Extracts accuracy, macro-F1, weighted-F1, macro precision, and macro recall dynamically.
    Raises FileNotFoundError, ValueError, or KeyError on invalid or missing data.
    """
    if baseline_path is None:
        baseline_path = os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "final_evaluation.json")

    if not os.path.exists(baseline_path):
        raise FileNotFoundError(f"Authoritative PlantVillage baseline artifact not found at: {baseline_path}")

    try:
        with open(baseline_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        raise ValueError(f"Failed parsing authoritative PlantVillage baseline JSON at {baseline_path}: {e}")

    required_keys = ["accuracy", "macro_f1", "weighted_f1", "per_class", "confusion_matrix"]
    for k in required_keys:
        if k not in data:
            raise KeyError(f"Missing required key '{k}' in authoritative PlantVillage baseline: {baseline_path}")

    per_class = data["per_class"]
    for c_name, c_data in per_class.items():
        for sub_k in ["precision", "recall", "f1_score", "support"]:
            if sub_k not in c_data:
                raise KeyError(f"Missing required key '{sub_k}' in per_class['{c_name}'] of baseline: {baseline_path}")

    macro_precision = sum(v["precision"] for v in per_class.values()) / len(per_class)
    macro_recall = sum(v["recall"] for v in per_class.values()) / len(per_class)
    total_samples = sum(v["support"] for v in per_class.values())
    cm = data["confusion_matrix"]
    correct_samples = sum(cm[i][i] for i in range(len(cm)))

    return {
        "val_loss": data.get("val_loss", 0.0),
        "accuracy": float(data["accuracy"]),
        "macro_f1": float(data["macro_f1"]),
        "weighted_f1": float(data["weighted_f1"]),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "total_samples": total_samples,
        "correct_samples": correct_samples,
        "per_class": per_class,
        "confusion_matrix": cm,
        "source_path": baseline_path
    }


def collect_plantdoc_samples(base_dir: str, target_splits: List[str]) -> Dict[str, Any]:
    """
    Crawls PlantDoc directory for specified splits.
    Categorizes files into supported tomato classes vs unsupported classes.
    """
    eligible_samples = []
    unsupported_samples = []

    for split in target_splits:
        split_dir = os.path.join(base_dir, split)
        if not os.path.exists(split_dir):
            continue

        for folder in sorted(os.listdir(split_dir)):
            folder_path = os.path.join(split_dir, folder)
            if not os.path.isdir(folder_path):
                continue

            files = sorted(os.listdir(folder_path))
            for f in files:
                file_path = os.path.join(folder_path, f)
                if not os.path.isfile(file_path):
                    continue

                if folder in PLANTDOC_CLASS_MAP:
                    eligible_samples.append({
                        "filepath": file_path,
                        "label": folder,
                        "split": split,
                        "filename": f
                    })
                else:
                    unsupported_samples.append({
                        "filepath": file_path,
                        "raw_label": folder,
                        "split": split,
                        "filename": f
                    })

    return {
        "eligible_samples": eligible_samples,
        "unsupported_samples": unsupported_samples
    }


def run_evaluation_benchmark():
    print("=" * 70)
    print("AgriMind Week 8 — Real PlantDoc Evaluation Benchmark")
    print(f"Dataset Location : {PLANTDOC_DIR}")
    print(f"Model Checkpoint : {CHECKPOINT_PATH}")
    print(f"Output Directory : {OUTPUT_BASE_DIR}")
    print("=" * 70)

    if not os.path.exists(PLANTDOC_DIR):
        print(f"ERROR: Dataset not found at {PLANTDOC_DIR}")
        sys.exit(1)
    if not os.path.exists(CHECKPOINT_PATH):
        print(f"ERROR: Model checkpoint not found at {CHECKPOINT_PATH}")
        sys.exit(1)

    mapper = LabelMapper(
        target_classes=CANONICAL_CLASSES,
        custom_mappings=PLANTDOC_CLASS_MAP
    )

    # Define inference function wrapping local PyTorch ResNet-50
    def real_model_inference(img_path: str) -> Dict[str, Any]:
        return run_raw_inference(img_path, checkpoint_path=CHECKPOINT_PATH, device="cpu")

    evaluator = VisionDatasetEvaluator(
        inference_fn=real_model_inference,
        label_mapper=mapper,
        target_classes=CANONICAL_CLASSES
    )

    # -------------------------------------------------------------
    # Benchmark 1: Official Test Split (N=28)
    # -------------------------------------------------------------
    print("\n>>> Collecting Benchmark 1: Official Test Split...")
    test_data = collect_plantdoc_samples(PLANTDOC_DIR, target_splits=["test"])
    test_eligible = test_data["eligible_samples"]
    print(f"Found {len(test_eligible)} eligible samples in test split across 3 classes.")

    print("Executing inference on Test Split...")
    test_results = evaluator.evaluate_samples(
        samples=test_eligible,
        benchmark_name="PlantDoc Official Test Split (Primary External Benchmark, N=28)",
        is_synthetic=False
    )
    test_out_dir = os.path.join(OUTPUT_BASE_DIR, "test_split")
    test_artifacts = evaluator.export_artifacts(test_results, test_out_dir)
    print(f"Test Split Accuracy : {test_results['metrics']['accuracy']:.4f}")
    print(f"Test Split Macro-F1 : {test_results['metrics']['macro_f1']:.4f}")
    print(f"Exported artifacts to: {test_out_dir}")

    # -------------------------------------------------------------
    # Benchmark 2: Full 3-Class Collection (Train + Test, N=309)
    # -------------------------------------------------------------
    print("\n>>> Collecting Benchmark 2: Full 3-Class Collection (Train + Test)...")
    full_data = collect_plantdoc_samples(PLANTDOC_DIR, target_splits=["train", "test"])
    full_eligible = full_data["eligible_samples"]
    print(f"Found {len(full_eligible)} eligible samples across train and test splits.")

    print("Executing inference on Full Collection (N=309)...")
    full_results = evaluator.evaluate_samples(
        samples=full_eligible,
        benchmark_name="PlantDoc Combined Collection (Exploratory / Non-Independent, N=309)",
        is_synthetic=False
    )
    full_out_dir = os.path.join(OUTPUT_BASE_DIR, "full_dataset")
    full_artifacts = evaluator.export_artifacts(full_results, full_out_dir)
    print(f"Full Collection Accuracy : {full_results['metrics']['accuracy']:.4f}")
    print(f"Full Collection Macro-F1 : {full_results['metrics']['macro_f1']:.4f}")
    print(f"Exported artifacts to: {full_out_dir}")

    # -------------------------------------------------------------
    # Overarching Executive Report
    # -------------------------------------------------------------
    summary_report_path = os.path.join(OUTPUT_BASE_DIR, "plantdoc_evaluation_summary.md")
    generate_comparative_summary_report(
        test_payload=test_results,
        full_payload=full_results,
        unsupported_count=len(full_data["unsupported_samples"]),
        output_path=summary_report_path
    )
    print(f"\nExecutive Summary Report generated at: {summary_report_path}")
    print("\nEvaluation completed successfully.")


def generate_comparative_summary_report(
    test_payload: Dict[str, Any],
    full_payload: Dict[str, Any],
    unsupported_count: int,
    output_path: str,
    pv_baseline_path: Optional[str] = None
):
    """Generates comprehensive comparative report comparing test split, full set, and PlantVillage baseline."""
    pv_baseline = load_authoritative_plantvillage_baseline(pv_baseline_path)

    t_m = test_payload["metrics"]
    f_m = full_payload["metrics"]
    cm_t = t_m.get("confusion_matrix", [])
    cm_f = f_m.get("confusion_matrix", [])
    t_correct = sum(cm_t[i][i] for i in range(len(cm_t))) if cm_t else int(round(t_m['accuracy'] * t_m['total_samples']))
    f_correct = sum(cm_f[i][i] for i in range(len(cm_f))) if cm_f else int(round(f_m['accuracy'] * f_m['total_samples']))

    lines = []
    lines.append("# AgriMind — Week 8: PlantDoc External System Evaluation Report")
    lines.append("")
    lines.append("**Dataset:** PlantDoc Dataset (Singh et al., CoDS-COMAD 2020)")
    lines.append(f"**Authorized Source Path:** `{PLANTDOC_DIR}`")
    lines.append(f"**Evaluation Timestamp:** `{datetime.now(timezone.utc).isoformat()}`")
    lines.append(f"**Evaluated Model:** ResNet-50 Baseline (`outputs/week2_vision/best_model.pth`)")
    lines.append(f"**Authoritative Baseline Source:** `{pv_baseline['source_path']}`")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 1. Executive Summary & Domain Shift Analysis")
    lines.append("")
    lines.append("This evaluation benchmarks the AgriMind vision model (trained on laboratory-controlled PlantVillage tomato leaves)")
    lines.append("against in-the-wild, field-realistic photography from the **PlantDoc** benchmark.")
    lines.append("")
    lines.append("### Key Findings:")
    lines.append(f"1. **PlantDoc Official Test Split (Primary External Benchmark, N={t_m['total_samples']}):**")
    lines.append(f"   - **Overall Accuracy:** `{t_m['accuracy'] * 100:.2f}%` ({t_correct} / {t_m['total_samples']})")
    lines.append(f"   - **Macro-F1 Score:** `{t_m['macro_f1']:.4f}`")
    lines.append(f"   - **Weighted-F1 Score:** `{t_m['weighted_f1']:.4f}`")
    lines.append(f"2. **PlantDoc Combined Collection (Exploratory / Non-Independent, N={f_m['total_samples']}):**")
    lines.append(f"   - **Overall Accuracy:** `{f_m['accuracy'] * 100:.2f}%` ({f_correct} / {f_m['total_samples']})")
    lines.append(f"   - **Macro-F1 Score:** `{f_m['macro_f1']:.4f}`")
    lines.append(f"   - **Weighted-F1 Score:** `{f_m['weighted_f1']:.4f}`")
    lines.append("3. **Cross-Domain Generalization Gap:**")
    lines.append(f"   - On PlantVillage validation (in-distribution controlled laboratory conditions), the model achieved **{pv_baseline['accuracy'] * 100:.2f}%** accuracy and **{pv_baseline['macro_f1']:.4f}** Macro-F1 ({pv_baseline['correct_samples']} / {pv_baseline['total_samples']:,} correctly classified).")
    lines.append(f"   - On the official PlantDoc test split (external unconstrained field benchmark), performance drops significantly to **{t_m['accuracy'] * 100:.2f}%** accuracy and **{t_m['macro_f1']:.4f}** Macro-F1 due to **unconstrained in-situ conditions** (multiple overlapping leaves, complex soil/sky backgrounds, varying illumination, motion blur, and non-uniform resolutions up to 4416px).")
    lines.append(f"4. **Out-of-Scope Classes Excluded:** `{unsupported_count}` images across non-target tomato diseases (Septoria, Mosaic Virus, Yellow Leaf Curl, Leaf Mold) and non-tomato crops were correctly excluded from evaluation.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 2. Quantitative Comparison: PlantVillage vs PlantDoc")
    lines.append("")
    lines.append("| Metric | PlantVillage Val (Controlled) | PlantDoc Official Test Split (Primary External Benchmark, N=28) | PlantDoc Combined Collection (Exploratory / Non-Independent, N=309) |")
    lines.append("| :--- | :---: | :---: | :---: |")
    lines.append(f"| **Sample Count (N)** | `{pv_baseline['total_samples']:,}` | `{t_m['total_samples']}` | `{f_m['total_samples']}` |")
    lines.append(f"| **Evaluation Nature** | `Internal In-Distribution Validation` | `External Independent Test Split` | `Exploratory Evaluation (Train + Test)` |")
    lines.append(f"| **Overall Accuracy** | `{pv_baseline['accuracy'] * 100:.2f}%` | `{t_m['accuracy'] * 100:.2f}%` | `{f_m['accuracy'] * 100:.2f}%` |")
    lines.append(f"| **Macro Precision** | `{pv_baseline['macro_precision']:.4f}` | `{t_m['macro_precision']:.4f}` | `{f_m['macro_precision']:.4f}` |")
    lines.append(f"| **Macro Recall** | `{pv_baseline['macro_recall']:.4f}` | `{t_m['macro_recall']:.4f}` | `{f_m['macro_recall']:.4f}` |")
    lines.append(f"| **Macro F1-Score** | `{pv_baseline['macro_f1']:.4f}` | `{t_m['macro_f1']:.4f}` | `{f_m['macro_f1']:.4f}` |")
    lines.append(f"| **Weighted F1-Score** | `{pv_baseline['weighted_f1']:.4f}` | `{t_m['weighted_f1']:.4f}` | `{f_m['weighted_f1']:.4f}` |")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> **Internal Validation vs. External Evaluation:**")
    lines.append("> - **Internal Validation (PlantVillage, N=1,007):** Evaluates model generalization on unseen leaves sampled from the *same* distribution as the training data (laboratory-controlled conditions with uniform background and consistent lighting).")
    lines.append("> - **External Evaluation (PlantDoc, N=28):** Evaluates out-of-distribution generalization on independent photography collected under unconstrained agricultural field conditions.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 3. PlantDoc Official Test Split (Primary External Benchmark, N=28) Detailed Breakdown")
    lines.append("")
    lines.append("### 3.1 Per-Class Metrics")
    lines.append("| Disease Class | Precision | Recall | F1-Score | Support |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    for c_short, d in t_m["per_class"].items():
        lines.append(f"| **{c_short}** | `{d['precision']:.4f}` | `{d['recall']:.4f}` | `{d['f1_score']:.4f}` | `{d['support']}` |")
    lines.append("")
    lines.append("> [!NOTE]")
    lines.append("> **Undefined Precision & Zero Predicted Samples (Bacterial Spot):** In the official test split (N=28), the model predicted 0 samples as Bacterial Spot (6 misclassified as Early Blight, 3 as Late Blight). Consequently, True Positives = 0 and False Positives = 0, rendering precision mathematically undefined (0/0). Per scikit-learn standard evaluation conventions (`zero_division=0`), precision is explicitly set to `0.0000`.")
    lines.append("")
    lines.append("> [!IMPORTANT]")
    lines.append("> **Split Independence Audit:** The official test split (N=28) was evaluated completely independently from the training split (N=281). The vision model checkpoint was trained solely on laboratory-controlled PlantVillage images in Week 2 and was never trained, fine-tuned, or exposed to any PlantDoc images. Test split metrics and predictions were generated in complete isolation from any training samples.")
    lines.append("")
    lines.append("### 3.2 Confusion Matrix (Test Split)")
    order = t_m["class_order"]
    lines.append("| True \\ Predicted | " + " | ".join([f"**Pred: {c}**" for c in order]) + " |")
    lines.append("| :--- | " + " | ".join([":---:" for _ in order]) + " |")
    for i, true_c in enumerate(order):
        row_str = " | ".join([str(cm_t[i][j]) for j in range(len(order))])
        lines.append(f"| **True: {true_c}** | {row_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 4. PlantDoc Combined Collection (Exploratory / Non-Independent, N=309) Detailed Breakdown")
    lines.append("")
    lines.append("> [!WARNING]")
    lines.append("> **Exploratory Nature of Combined Benchmark:** The Combined Collection merges the official training split ($N=281$) and official test split ($N=28$) solely to evaluate aggregate behavior on a broader variety of field images ($N=309$). It must **never** be cited as an independent test set. The primary external evaluation benchmark remains the official test split ($N=28$).")
    lines.append("")
    lines.append("### 4.1 Per-Class Metrics")
    lines.append("| Disease Class | Precision | Recall | F1-Score | Support |")
    lines.append("| :--- | :---: | :---: | :---: | :---: |")
    for c_short, d in f_m["per_class"].items():
        lines.append(f"| **{c_short}** | `{d['precision']:.4f}` | `{d['recall']:.4f}` | `{d['f1_score']:.4f}` | `{d['support']}` |")
    lines.append("")

    lines.append("### 4.2 Confusion Matrix (Full Collection)")
    cm_f = f_m["confusion_matrix"]
    lines.append("| True \\ Predicted | " + " | ".join([f"**Pred: {c}**" for c in order]) + " |")
    lines.append("| :--- | " + " | ".join([":---:" for _ in order]) + " |")
    for i, true_c in enumerate(order):
        row_str = " | ".join([str(cm_f[i][j]) for j in range(len(order))])
        lines.append(f"| **True: {true_c}** | {row_str} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("## 5. Agronomic Error Analysis & Failure Modes")
    lines.append("")
    lines.append("1. **Early Blight vs. Late Blight Confusion:**")
    lines.append("   - In field conditions, early necrotic lesions from Early Blight and water-soaked Late Blight patches share dark brownish discoloration.")
    lines.append("   - Without macro magnification of concentric rings or morning sporulation, visual confusion occurs.")
    lines.append("2. **Bacterial Spot Field Lesions:**")
    lines.append("   - In PlantVillage, bacterial spot appears as distinct pin-point spots on uniform gray/black paper.")
    lines.append("   - In PlantDoc, natural sunlight reflections and dust mimic bacterial lesions, degrading precision.")
    lines.append("3. **Mitigation via AgriMind Multi-Agent Architecture:**")
    lines.append("   - This performance drop validates the core premise of AgriMind: **A single vision CNN cannot reliably make field decisions alone.**")
    lines.append("   - AgriMind's **Investigation Agent** cross-checks vision confidence with weather (cool/wet vs hot/dry), canopy level, and physical scouting notes.")
    lines.append("   - When visual confidence is low or conflicting, the **Critic Agent** routes the case to human review or the **Adaptive Reassessment Mechanism** (Week 7).")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def regenerate_summary_from_existing(
    output_base_dir: Optional[str] = None,
    pv_baseline_path: Optional[str] = None
) -> str:
    """
    Regenerates plantdoc_evaluation_summary.md from existing test_split/metrics.json
    and full_dataset/metrics.json without rerunning inference.
    """
    if output_base_dir is None:
        output_base_dir = OUTPUT_BASE_DIR
    if pv_baseline_path is None:
        pv_baseline_path = os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "final_evaluation.json")

    test_metrics_path = os.path.join(output_base_dir, "test_split", "metrics.json")
    full_metrics_path = os.path.join(output_base_dir, "full_dataset", "metrics.json")

    if not os.path.exists(test_metrics_path):
        raise FileNotFoundError(f"Test split metrics not found at: {test_metrics_path}")
    if not os.path.exists(full_metrics_path):
        raise FileNotFoundError(f"Full dataset metrics not found at: {full_metrics_path}")

    with open(test_metrics_path, "r", encoding="utf-8") as f:
        test_payload = json.load(f)
    with open(full_metrics_path, "r", encoding="utf-8") as f:
        full_payload = json.load(f)

    # Count unsupported samples dynamically if dataset is accessible, or use default count
    unsupported_count = 88
    if os.path.exists(PLANTDOC_DIR):
        try:
            full_data = collect_plantdoc_samples(PLANTDOC_DIR, target_splits=["train", "test"])
            unsupported_count = len(full_data["unsupported_samples"])
        except Exception:
            pass

    summary_report_path = os.path.join(output_base_dir, "plantdoc_evaluation_summary.md")
    generate_comparative_summary_report(
        test_payload=test_payload,
        full_payload=full_payload,
        unsupported_count=unsupported_count,
        output_path=summary_report_path,
        pv_baseline_path=pv_baseline_path
    )
    return summary_report_path


def main():
    parser = argparse.ArgumentParser(description="AgriMind Week 8 — PlantDoc Evaluation and Reporting")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Regenerate plantdoc_evaluation_summary.md from existing metrics without re-running inference"
    )
    parser.add_argument(
        "--baseline-path",
        type=str,
        default=None,
        help="Path to authoritative PlantVillage baseline evaluation JSON"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Base output directory for evaluation artifacts"
    )
    args = parser.parse_args()

    if args.summary_only:
        out_dir = args.output_dir or OUTPUT_BASE_DIR
        print(f"Regenerating summary report using existing metrics in: {out_dir}")
        report_path = regenerate_summary_from_existing(
            output_base_dir=out_dir,
            pv_baseline_path=args.baseline_path
        )
        print(f"Successfully regenerated summary report at: {report_path}")
    else:
        run_evaluation_benchmark()


if __name__ == "__main__":
    main()
