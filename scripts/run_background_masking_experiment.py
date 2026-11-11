"""
AgriMind — Phase 2: Controlled Background-Masking Diagnostic Experiment Script.
Evaluates the impact of background regions on the frozen ResNet-50 classifier
across the official PlantDoc test split (N=28).

Experimental Conditions:
- Condition A: Original Baseline (Resize 256 -> CenterCrop 224 -> Normalize)
- Condition B: Background Masked (Leaf preserved, background set to neutral studio gray [135, 135, 135])
- Condition C: Background Only (Background preserved, leaf suppressed to neutral studio gray [135, 135, 135])
"""
import os
import sys
import json
import csv
import time
import numpy as np
import scipy.ndimage as ndi
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

import torch
from torchvision import transforms

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.vision.model import create_model
from src.vision.dataset import IMAGENET_MEAN, IMAGENET_STD, IDX_TO_LABEL, LABEL_TO_IDX
from src.vision.evaluation_framework import (
    MetricCalculator,
    CANONICAL_CLASSES,
    CANONICAL_SHORT_NAMES
)

CHECKPOINT_PATH = os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "best_model.pth")
TEST_PREDICTIONS_CSV = os.path.join(WORKSPACE_DIR, "outputs", "week8_plantdoc_evaluation", "test_split", "predictions.csv")
OUTPUT_BASE_DIR = os.path.join(WORKSPACE_DIR, "outputs", "phase2_background_masking")

NEUTRAL_STUDIO_GRAY = np.array([135, 135, 135], dtype=np.uint8)


# ---------------------------------------------------------------------------
# Deterministic Segmentation Algorithm
# ---------------------------------------------------------------------------

def segment_leaf(img_pil: Image.Image) -> np.ndarray:
    """
    Deterministic botanical segmentation distinguishing tomato foliage from field backgrounds.
    Uses HSV color space, RGB chromatic balance, and morphological hole-filling.
    Guarantees internal foliar necrotic lesions/spots are preserved via binary_fill_holes.
    Returns: bool ndarray (H, W) where True = Leaf, False = Background.
    """
    rgb = np.array(img_pil.convert("RGB"), dtype=np.float32) / 255.0
    hsv = np.array(img_pil.convert("HSV"), dtype=np.float32)

    # PIL HSV: H in [0, 255] (maps to 0-360 deg), S in [0, 255], V in [0, 255]
    h = hsv[:, :, 0] / 255.0 * 360.0
    s = hsv[:, :, 1] / 255.0
    v = hsv[:, :, 2] / 255.0

    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

    # Background detection filters
    is_sky_or_white = (v > 0.75) & (s < 0.20)
    is_blue_sky = (h > 180) & (h < 260) & (b > g)
    is_deep_shadow = (v < 0.15)

    # Foliar feature detection filters
    # 1. Broad foliage hue (25 to 165 deg: yellow-green, green, olive)
    is_foliage_hue = (h >= 25) & (h <= 165) & (s > 0.12) & (v > 0.15)
    # 2. Green channel dominance (captures desaturated or shadowed leaves)
    is_green_dominant = (g > r * 0.95) & (g > b * 1.05) & (s > 0.10)
    # 3. Necrotic / chlorotic lesion tissue (brown/yellow/rust with moderate saturation)
    is_necrotic = (h >= 10) & (h <= 45) & (s > 0.20) & (v > 0.15) & (r > b)

    raw_leaf = (is_foliage_hue | is_green_dominant | is_necrotic) & ~(is_sky_or_white | is_blue_sky | is_deep_shadow)

    # Morphological processing
    struct = ndi.generate_binary_structure(2, 2)
    closed = ndi.binary_closing(raw_leaf, structure=struct, iterations=3)
    # CRITICAL: binary_fill_holes ensures necrotic spots inside the leaf blade are NOT carved out
    filled = ndi.binary_fill_holes(closed)
    cleaned = ndi.binary_opening(filled, structure=struct, iterations=1)
    final_mask = ndi.binary_fill_holes(cleaned)

    # Coverage fallback: if mask is degenerate (< 5% of canvas), fall back to raw leaf fill
    if final_mask.mean() < 0.05:
        final_mask = ndi.binary_fill_holes(raw_leaf)

    return final_mask.astype(bool)


# ---------------------------------------------------------------------------
# Preprocessing Transforms
# ---------------------------------------------------------------------------

def get_eval_transforms():
    """Baseline deterministic evaluation transforms."""
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def create_diagnostic_images(orig_img: Image.Image, mask: np.ndarray):
    """
    Generates Condition B (Masked Background) and Condition C (Background Only).
    Fill value is neutral studio gray [135, 135, 135] matching PlantVillage laboratory background.
    """
    orig_np = np.array(orig_img.convert("RGB"))

    # Condition B: Leaf preserved, background replaced with neutral gray
    masked_np = orig_np.copy()
    masked_np[~mask] = NEUTRAL_STUDIO_GRAY
    masked_img = Image.fromarray(masked_np)

    # Condition C: Background preserved, leaf suppressed with neutral gray
    bg_only_np = orig_np.copy()
    bg_only_np[mask] = NEUTRAL_STUDIO_GRAY
    bg_only_img = Image.fromarray(bg_only_np)

    # Binary mask image (255 for leaf, 0 for background)
    mask_uint8 = (mask.astype(np.uint8) * 255)
    mask_img = Image.fromarray(mask_uint8, mode="L")

    return masked_img, bg_only_img, mask_img


# ---------------------------------------------------------------------------
# Visual Figure Generation
# ---------------------------------------------------------------------------

def save_comparison_figure(
    orig_pil: Image.Image,
    mask_pil: Image.Image,
    masked_pil: Image.Image,
    bg_only_pil: Image.Image,
    sample_id: str,
    filename: str,
    ground_truth: str,
    cond_a_res: dict,
    cond_b_res: dict,
    cond_c_res: dict,
    out_path: str
):
    """Saves a 4-panel visual comparison figure: Original | Mask | Cond B (Masked) | Cond C (Background Only)."""
    fig, axes = plt.subplots(1, 4, figsize=(20, 5), dpi=150)

    # Panel 1: Original Image
    axes[0].imshow(orig_pil)
    axes[0].set_title(f"Orig: {cond_a_res['pred_short']} ({cond_a_res['conf']*100:.1f}%)", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Panel 2: Binary Segmentation Mask
    axes[1].imshow(mask_pil, cmap="gray")
    cov = float(np.array(mask_pil).mean() / 255.0) * 100.0
    axes[1].set_title(f"Leaf Mask (Coverage: {cov:.1f}%)", fontsize=11, fontweight="bold")
    axes[1].axis("off")

    # Panel 3: Condition B (Background Masked, Leaf Preserved)
    axes[2].imshow(masked_pil)
    axes[2].set_title(f"Cond B (Masked): {cond_b_res['pred_short']} ({cond_b_res['conf']*100:.1f}%)", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    # Panel 4: Condition C (Background Preserved, Leaf Suppressed)
    axes[3].imshow(bg_only_pil)
    axes[3].set_title(f"Cond C (Bg-Only): {cond_c_res['pred_short']} ({cond_c_res['conf']*100:.1f}%)", fontsize=11, fontweight="bold")
    axes[3].axis("off")

    gt_short = ground_truth.replace("Tomato___", "")
    chg_b = "CHANGED" if cond_b_res['pred_short'] != cond_a_res['pred_short'] else "UNCHANGED"

    fig.suptitle(
        f"{sample_id} | {filename}\n"
        f"Ground Truth: {gt_short} | Cond A: {cond_a_res['pred_short']} | Cond B: {cond_b_res['pred_short']} [{chg_b}] | Cond C: {cond_c_res['pred_short']}",
        fontsize=12,
        fontweight="bold",
        y=1.03
    )

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main Experiment Execution
# ---------------------------------------------------------------------------

def run_background_masking_experiment():
    print("=" * 70)
    print("AgriMind — Phase 2: Controlled Background-Masking Diagnostic Experiment")
    print(f"Checkpoint : {CHECKPOINT_PATH}")
    print(f"Output Dir : {OUTPUT_BASE_DIR}")
    print("=" * 70)

    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Checkpoint not found at: {CHECKPOINT_PATH}")
    if not os.path.exists(TEST_PREDICTIONS_CSV):
        raise FileNotFoundError(f"Test split manifest missing: {TEST_PREDICTIONS_CSV}")

    # Create subdirectories
    subdirs = {
        "orig": os.path.join(OUTPUT_BASE_DIR, "original_images"),
        "masks": os.path.join(OUTPUT_BASE_DIR, "masks"),
        "masked": os.path.join(OUTPUT_BASE_DIR, "masked_images"),
        "bg_only": os.path.join(OUTPUT_BASE_DIR, "background_only"),
        "figures": os.path.join(OUTPUT_BASE_DIR, "comparison_figures"),
        "per_sample": os.path.join(OUTPUT_BASE_DIR, "per_sample_results"),
        "metrics": os.path.join(OUTPUT_BASE_DIR, "metrics"),
    }
    for p in subdirs.values():
        os.makedirs(p, exist_ok=True)

    # 1. Load Model
    print("\n[1/5] Loading frozen ResNet-50 checkpoint...")
    model = create_model(num_classes=3, pretrained=False)
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt)
    model.eval()
    print("Model placed in evaluation mode on CPU.")

    # 2. Load Manifest
    print("\n[2/5] Loading 28 official test samples...")
    samples = []
    with open(TEST_PREDICTIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            samples.append(r)
    print(f"Loaded {len(samples)} samples in exact sequential order.")

    eval_tf = get_eval_transforms()

    # Data collection containers
    results_a = []
    results_b = []
    results_c = []
    timing_a = []
    timing_b = []
    timing_c = []
    masking_times = []

    per_sample_master = []

    print("\n[3/5] Evaluating all 28 samples across Conditions A, B, and C...")
    for idx, s in enumerate(samples):
        img_path = s["filepath"]
        sample_id = s["sample_id"]
        filename = os.path.basename(img_path)
        gt_mapped = s["ground_truth_mapped"]
        gt_idx = LABEL_TO_IDX[gt_mapped]

        orig_pil = Image.open(img_path).convert("RGB")

        # Save original copy
        orig_save_path = os.path.join(subdirs["orig"], f"{sample_id}_{filename}")
        orig_pil.save(orig_save_path)

        # Condition A: Original Baseline
        t0 = time.perf_counter()
        t_a = eval_tf(orig_pil).unsqueeze(0)
        with torch.no_grad():
            out_a = model(t_a)
            probs_a = torch.softmax(out_a, dim=1)[0].numpy()
        t1 = time.perf_counter()
        timing_a.append((t1 - t0) * 1000.0)

        pred_idx_a = int(probs_a.argmax())
        res_a = {
            "pred_idx": pred_idx_a,
            "pred_label": IDX_TO_LABEL[pred_idx_a],
            "pred_short": IDX_TO_LABEL[pred_idx_a].replace("Tomato___", ""),
            "conf": float(probs_a[pred_idx_a]),
            "true_prob": float(probs_a[gt_idx]),
            "is_correct": bool(pred_idx_a == gt_idx),
            "probs": {IDX_TO_LABEL[i].replace("Tomato___", ""): round(float(probs_a[i]), 4) for i in range(3)}
        }
        results_a.append(res_a)

        # Generate Mask & Diagnostic Images
        t_mask0 = time.perf_counter()
        mask = segment_leaf(orig_pil)
        masked_pil, bg_only_pil, mask_pil = create_diagnostic_images(orig_pil, mask)
        t_mask1 = time.perf_counter()
        masking_times.append((t_mask1 - t_mask0) * 1000.0)

        # Save Diagnostic Images
        mask_path = os.path.join(subdirs["masks"], f"{sample_id}_{filename.replace('.jpg', '').replace('.JPG', '')}_mask.png")
        masked_path = os.path.join(subdirs["masked"], f"{sample_id}_{filename}")
        bg_only_path = os.path.join(subdirs["bg_only"], f"{sample_id}_{filename}")

        mask_pil.save(mask_path)
        masked_pil.save(masked_path)
        bg_only_pil.save(bg_only_path)

        # Condition B: Background Masked
        t2 = time.perf_counter()
        t_b = eval_tf(masked_pil).unsqueeze(0)
        with torch.no_grad():
            out_b = model(t_b)
            probs_b = torch.softmax(out_b, dim=1)[0].numpy()
        t3 = time.perf_counter()
        timing_b.append((t3 - t2) * 1000.0)

        pred_idx_b = int(probs_b.argmax())
        res_b = {
            "pred_idx": pred_idx_b,
            "pred_label": IDX_TO_LABEL[pred_idx_b],
            "pred_short": IDX_TO_LABEL[pred_idx_b].replace("Tomato___", ""),
            "conf": float(probs_b[pred_idx_b]),
            "true_prob": float(probs_b[gt_idx]),
            "is_correct": bool(pred_idx_b == gt_idx),
            "probs": {IDX_TO_LABEL[i].replace("Tomato___", ""): round(float(probs_b[i]), 4) for i in range(3)},
            "agrees_with_a": bool(pred_idx_b == pred_idx_a)
        }
        results_b.append(res_b)

        # Condition C: Background Only
        t4 = time.perf_counter()
        t_c = eval_tf(bg_only_pil).unsqueeze(0)
        with torch.no_grad():
            out_c = model(t_c)
            probs_c = torch.softmax(out_c, dim=1)[0].numpy()
        t5 = time.perf_counter()
        timing_c.append((t5 - t4) * 1000.0)

        pred_idx_c = int(probs_c.argmax())
        res_c = {
            "pred_idx": pred_idx_c,
            "pred_label": IDX_TO_LABEL[pred_idx_c],
            "pred_short": IDX_TO_LABEL[pred_idx_c].replace("Tomato___", ""),
            "conf": float(probs_c[pred_idx_c]),
            "true_prob": float(probs_c[gt_idx]),
            "is_correct": bool(pred_idx_c == gt_idx),
            "probs": {IDX_TO_LABEL[i].replace("Tomato___", ""): round(float(probs_c[i]), 4) for i in range(3)},
            "agrees_with_a": bool(pred_idx_c == pred_idx_a)
        }
        results_c.append(res_c)

        # Save 4-Panel Comparison Figure
        fig_path = os.path.join(subdirs["figures"], f"{sample_id}_{filename.replace('.jpg', '').replace('.JPG', '')}_4panel.png")
        save_comparison_figure(
            orig_pil=orig_pil,
            mask_pil=mask_pil,
            masked_pil=masked_pil,
            bg_only_pil=bg_only_pil,
            sample_id=sample_id,
            filename=filename,
            ground_truth=gt_mapped,
            cond_a_res=res_a,
            cond_b_res=res_b,
            cond_c_res=res_c,
            out_path=fig_path
        )

        # Per-Sample JSON Record
        sample_record = {
            "sample_id": sample_id,
            "filename": filename,
            "filepath": img_path,
            "ground_truth": gt_mapped,
            "ground_truth_short": gt_mapped.replace("Tomato___", ""),
            "leaf_coverage_pct": round(float(mask.mean()) * 100.0, 2),
            "condition_a_baseline": res_a,
            "condition_b_masked": res_b,
            "condition_c_bg_only": res_c,
            "prediction_changed_b_vs_a": bool(res_b["pred_short"] != res_a["pred_short"]),
            "artifacts": {
                "original": orig_save_path,
                "mask": mask_path,
                "masked_image": masked_path,
                "background_only": bg_only_path,
                "comparison_figure": fig_path
            }
        }
        per_sample_master.append(sample_record)

        json_out = os.path.join(subdirs["per_sample"], f"{sample_id}_{filename.replace('.jpg', '').replace('.JPG', '')}.json")
        with open(json_out, "w", encoding="utf-8") as f:
            json.dump(sample_record, f, indent=2)

        chg_str = "-> CHANGED" if res_b["pred_short"] != res_a["pred_short"] else "(unchanged)"
        print(f"  [{idx+1:02d}/28] {sample_id} ({filename}) | A: {res_a['pred_short']} ({res_a['conf']*100:.1f}%) | B: {res_b['pred_short']} ({res_b['conf']*100:.1f}%) {chg_str} | C: {res_c['pred_short']} ({res_c['conf']*100:.1f}%)")

    # 4. Compute Comprehensive Metrics
    print("\n[4/5] Computing dataset-level metrics for Conditions A, B, and C...")
    gt_list = [s["ground_truth_mapped"] for s in samples]
    preds_a = [r["pred_label"] for r in results_a]
    preds_b = [r["pred_label"] for r in results_b]
    preds_c = [r["pred_label"] for r in results_c]

    metrics_a = MetricCalculator.compute_metrics(gt_list, preds_a, CANONICAL_CLASSES)
    metrics_b = MetricCalculator.compute_metrics(gt_list, preds_b, CANONICAL_CLASSES)
    metrics_c = MetricCalculator.compute_metrics(gt_list, preds_c, CANONICAL_CLASSES)

    # Agreement calculation
    agree_b_count = sum(1 for r in results_b if r["agrees_with_a"])
    agree_c_count = sum(1 for r in results_c if r["agrees_with_a"])

    timing_summary = {
        "condition_a_inference_ms": {
            "mean": round(float(np.mean(timing_a)), 2),
            "median": round(float(np.median(timing_a)), 2),
            "std": round(float(np.std(timing_a)), 2)
        },
        "condition_b_inference_ms": {
            "mean": round(float(np.mean(timing_b)), 2),
            "median": round(float(np.median(timing_b)), 2),
            "std": round(float(np.std(timing_b)), 2)
        },
        "condition_c_inference_ms": {
            "mean": round(float(np.mean(timing_c)), 2),
            "median": round(float(np.median(timing_c)), 2),
            "std": round(float(np.std(timing_c)), 2)
        },
        "masking_processing_ms": {
            "mean": round(float(np.mean(masking_times)), 2),
            "median": round(float(np.median(masking_times)), 2),
            "std": round(float(np.std(masking_times)), 2)
        }
    }

    experiment_metrics = {
        "experiment_title": "AgriMind Phase 2: Controlled Background-Masking Diagnostic Experiment",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "checkpoint_evaluated": CHECKPOINT_PATH,
        "sample_count": len(samples),
        "masking_parameters": {
            "method": "Deterministic Botanical HSV+RGB Color Indexing with Morphological Hole-Filling",
            "background_fill_color_rgb": [135, 135, 135],
            "background_fill_description": "Neutral studio gray matching PlantVillage training background mean border RGB",
            "morphological_structure": "3x3 8-connected, binary_closing iterations=3, binary_fill_holes, binary_opening iterations=1"
        },
        "condition_a_baseline": {
            "description": "Original image with baseline evaluation preprocessing (Resize 256, CenterCrop 224)",
            "metrics": metrics_a,
            "agreement_with_a_pct": 100.0,
            "agreement_with_a_count": 28
        },
        "condition_b_masked": {
            "description": "Background masked to neutral studio gray [135, 135, 135], leaf preserved exactly",
            "metrics": metrics_b,
            "agreement_with_a_pct": round(agree_b_count / 28.0 * 100.0, 2),
            "agreement_with_a_count": agree_b_count,
            "prediction_changes_count": 28 - agree_b_count
        },
        "condition_c_bg_only": {
            "description": "Leaf suppressed to neutral studio gray [135, 135, 135], background preserved exactly (OOD Diagnostic)",
            "metrics": metrics_c,
            "agreement_with_a_pct": round(agree_c_count / 28.0 * 100.0, 2),
            "agreement_with_a_count": agree_c_count
        },
        "timing_benchmarks": timing_summary
    }

    # Save metrics JSON
    with open(os.path.join(OUTPUT_BASE_DIR, "experiment_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(experiment_metrics, f, indent=2)

    with open(os.path.join(subdirs["metrics"], "metrics_condition_a.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_a, f, indent=2)
    with open(os.path.join(subdirs["metrics"], "metrics_condition_b.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_b, f, indent=2)
    with open(os.path.join(subdirs["metrics"], "metrics_condition_c.json"), "w", encoding="utf-8") as f:
        json.dump(metrics_c, f, indent=2)

    # 5. Export Master CSV
    print("\n[5/5] Exporting master CSV manifest and reports...")
    csv_rows = []
    for r in per_sample_master:
        csv_rows.append({
            "sample_id": r["sample_id"],
            "filename": r["filename"],
            "ground_truth": r["ground_truth_short"],
            "leaf_coverage_pct": r["leaf_coverage_pct"],
            "cond_a_pred": r["condition_a_baseline"]["pred_short"],
            "cond_a_conf": round(r["condition_a_baseline"]["conf"], 4),
            "cond_a_correct": r["condition_a_baseline"]["is_correct"],
            "cond_b_pred": r["condition_b_masked"]["pred_short"],
            "cond_b_conf": round(r["condition_b_masked"]["conf"], 4),
            "cond_b_correct": r["condition_b_masked"]["is_correct"],
            "cond_b_changed": r["prediction_changed_b_vs_a"],
            "cond_c_pred": r["condition_c_bg_only"]["pred_short"],
            "cond_c_conf": round(r["condition_c_bg_only"]["conf"], 4),
            "cond_c_correct": r["condition_c_bg_only"]["is_correct"]
        })

    csv_path = os.path.join(OUTPUT_BASE_DIR, "per_sample_predictions.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sample_id", "filename", "ground_truth", "leaf_coverage_pct",
            "cond_a_pred", "cond_a_conf", "cond_a_correct",
            "cond_b_pred", "cond_b_conf", "cond_b_correct", "cond_b_changed",
            "cond_c_pred", "cond_c_conf", "cond_c_correct"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Exported per-sample CSV to: {csv_path}")
    print("Experiment execution completed successfully.")
    return experiment_metrics, per_sample_master


if __name__ == "__main__":
    run_background_masking_experiment()

