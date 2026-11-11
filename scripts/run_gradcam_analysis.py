"""
AgriMind — Grad-CAM Visual Explainability Analysis Script (Phase 1).
Investigates model attention, spatial attribution, and misclassification patterns
on the official PlantDoc external test split (N=28), focusing on the 9 Bacterial Spot
failure cases and comparative Blight benchmarks.

Target Layer: model.layer4[-1] (Final Bottleneck block of ResNet-50 before avgpool).
Evaluated Checkpoint: outputs/week2_vision/best_model.pth (Frozen, Eval mode).
"""
import os
import sys
import json
import csv
import torch
import torch.nn.functional as F
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
from torchvision import transforms

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.vision.model import create_model
from src.vision.dataset import IMAGENET_MEAN, IMAGENET_STD, IDX_TO_LABEL, LABEL_TO_IDX

CHECKPOINT_PATH = os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "best_model.pth")
TEST_PREDICTIONS_CSV = os.path.join(WORKSPACE_DIR, "outputs", "week8_plantdoc_evaluation", "test_split", "predictions.csv")
OUTPUT_BASE_DIR = os.path.join(WORKSPACE_DIR, "outputs", "gradcam_analysis")


# ---------------------------------------------------------------------------
# Grad-CAM Engine
# ---------------------------------------------------------------------------

class GradCAM:
    """Isolated Grad-CAM attribution generator with forward/backward hooks."""

    def __init__(self, model: torch.nn.Module, target_layer: torch.nn.Module):
        self.model = model
        self.target_layer = target_layer
        self.activations = None
        self.gradients = None
        self.hook_handles = []
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, inp, out):
            self.activations = out.detach()

        def backward_hook(module, grad_inp, grad_out):
            self.gradients = grad_out[0].detach()

        self.hook_handles.append(self.target_layer.register_forward_hook(forward_hook))
        self.hook_handles.append(self.target_layer.register_full_backward_hook(backward_hook))

    def generate_cam(self, input_tensor: torch.Tensor, target_class_idx: int) -> np.ndarray:
        """Computes normalized Grad-CAM heatmap interpolated to input resolution (224, 224)."""
        self.model.zero_grad()
        outputs = self.model(input_tensor)
        score = outputs[0, target_class_idx]
        score.backward(retain_graph=True)

        # Global average pooling of gradients: [1, 2048, 7, 7] -> [2048]
        weights = torch.mean(self.gradients, dim=(2, 3))[0]

        # Linear combination of forward activation maps
        cam = torch.zeros(self.activations.shape[2:], dtype=torch.float32, device=self.activations.device)
        for i, w in enumerate(weights):
            cam += w * self.activations[0, i, :, :]

        # Rectified Linear Unit
        cam = torch.relu(cam)
        cam_np = cam.cpu().numpy()

        # Min-max normalization
        cam_min, cam_max = float(cam_np.min()), float(cam_np.max())
        if cam_max > cam_min:
            cam_norm = (cam_np - cam_min) / (cam_max - cam_min)
        else:
            cam_norm = np.zeros_like(cam_np)

        # Bilinear interpolation to 224x224
        t_cam = torch.from_numpy(cam_norm).unsqueeze(0).unsqueeze(0)
        cam_upscaled = F.interpolate(t_cam, size=(224, 224), mode="bilinear", align_corners=False)
        return cam_upscaled[0, 0].cpu().numpy()

    def remove_hooks(self):
        for h in self.hook_handles:
            h.remove()
        self.hook_handles.clear()


# ---------------------------------------------------------------------------
# Preprocessing Transforms
# ---------------------------------------------------------------------------

def get_baseline_transform():
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def get_direct_resize_transform():
    return transforms.Compose([
        transforms.Resize((224, 224), interpolation=transforms.InterpolationMode.BILINEAR),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def denormalize_image(tensor: torch.Tensor) -> np.ndarray:
    """Converts normalized (3, 224, 224) PyTorch tensor to RGB numpy array [0, 1]."""
    img_np = tensor[0].cpu().numpy().transpose(1, 2, 0)
    mean = np.array(IMAGENET_MEAN)
    std = np.array(IMAGENET_STD)
    img_rgb = np.clip(img_np * std + mean, 0.0, 1.0)
    return img_rgb


# ---------------------------------------------------------------------------
# Quantitative Attribution Metrics
# ---------------------------------------------------------------------------

def compute_attribution_metrics(heatmap: np.ndarray) -> dict:
    """Computes quantitative spatial distribution metrics from the 224x224 heatmap."""
    h, w = heatmap.shape
    peak_y, peak_x = np.unravel_index(heatmap.argmax(), heatmap.shape)

    # Define border region as outer 28 pixels (12.5% border margin)
    border_mask = np.zeros((h, w), dtype=bool)
    border_mask[:28, :] = True
    border_mask[-28:, :] = True
    border_mask[:, :28] = True
    border_mask[:, -28:] = True

    center_mask = ~border_mask

    border_mean = float(np.mean(heatmap[border_mask]))
    center_mean = float(np.mean(heatmap[center_mask]))
    border_ratio = round(border_mean / (center_mean + 1e-8), 3)

    is_peak_on_border = bool(border_mask[peak_y, peak_x])

    # Classify focus pattern
    if is_peak_on_border and border_ratio >= 1.0:
        focus_region = "Background / Border"
    elif border_ratio >= 1.2:
        focus_region = "Periphery / Background Dominant"
    elif not is_peak_on_border and border_ratio < 0.6:
        focus_region = "Foliar Center / Lesion Focus"
    elif not is_peak_on_border:
        focus_region = "Leaf Interior / Tissue"
    else:
        focus_region = "Dispersed / Ambiguous"

    return {
        "peak_y": int(peak_y),
        "peak_x": int(peak_x),
        "is_peak_on_border": is_peak_on_border,
        "border_mean": round(border_mean, 4),
        "center_mean": round(center_mean, 4),
        "border_to_center_ratio": border_ratio,
        "focus_region": focus_region
    }


# ---------------------------------------------------------------------------
# Visual Figure Generation
# ---------------------------------------------------------------------------

def save_visual_figure(
    original_rgb: np.ndarray,
    heatmap: np.ndarray,
    overlay_rgb: np.ndarray,
    sample_id: str,
    filename: str,
    ground_truth: str,
    pred_label: str,
    confidence: float,
    true_prob: float,
    cam_target_name: str,
    out_path: str
):
    """Saves a high-resolution 3-panel figure: Preprocessed RGB | Heatmap | Alpha Overlay."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5), dpi=150)

    # Panel 1: Original Preprocessed RGB
    axes[0].imshow(original_rgb)
    axes[0].set_title(f"Input RGB ({original_rgb.shape[0]}x{original_rgb.shape[1]})", fontsize=11, fontweight="bold")
    axes[0].axis("off")

    # Panel 2: Heatmap
    im1 = axes[1].imshow(heatmap, cmap="jet", vmin=0.0, vmax=1.0)
    axes[1].set_title(f"Grad-CAM Heatmap [{cam_target_name}]", fontsize=11, fontweight="bold")
    axes[1].axis("off")
    fig.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    # Panel 3: Alpha-Blended Overlay
    axes[2].imshow(overlay_rgb)
    axes[2].set_title("Overlay (60% RGB + 40% CAM)", fontsize=11, fontweight="bold")
    axes[2].axis("off")

    gt_short = ground_truth.replace("Tomato___", "")
    pred_short = pred_label.replace("Tomato___", "")
    status_str = "CORRECT" if gt_short == pred_short else "INCORRECT"

    fig.suptitle(
        f"{sample_id} | {filename}\n"
        f"GT: {gt_short} | Pred: {pred_short} (Conf: {confidence*100:.1f}%) | True-Class Prob: {true_prob*100:.2f}% | [{status_str}]",
        fontsize=12,
        fontweight="bold",
        y=1.02
    )

    plt.tight_layout()
    plt.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main Analysis Execution
# ---------------------------------------------------------------------------

def run_gradcam_analysis():
    print("=" * 70)
    print("AgriMind — Grad-CAM Visual Explainability Analysis (Phase 1)")
    print(f"Checkpoint : {CHECKPOINT_PATH}")
    print(f"Output Dir : {OUTPUT_BASE_DIR}")
    print("=" * 70)

    # Verify Checkpoint Exists
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Model checkpoint not found at: {CHECKPOINT_PATH}")

    # Create Directories
    os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
    dirs = {
        "heatmaps": os.path.join(OUTPUT_BASE_DIR, "heatmaps"),
        "overlays": os.path.join(OUTPUT_BASE_DIR, "overlays"),
        "figures": os.path.join(OUTPUT_BASE_DIR, "figures"),
        "direct_resize": os.path.join(OUTPUT_BASE_DIR, "direct_resize_figures"),
        "json": os.path.join(OUTPUT_BASE_DIR, "per_sample_json")
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)

    # 1. Load Model & Attach Grad-CAM
    print("\n[1/4] Loading ResNet-50 model checkpoint...")
    model = create_model(num_classes=3, pretrained=False)
    ckpt = torch.load(CHECKPOINT_PATH, map_location="cpu")
    model.load_state_dict(ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt)
    model.eval()

    target_layer = model.layer4[-1]
    print(f"Attached Grad-CAM hooks to target layer: {type(target_layer).__name__} (layer4[-1])")
    cam_engine = GradCAM(model, target_layer)

    # 2. Load the 28 Test Samples
    print("\n[2/4] Loading test samples from predictions manifest...")
    if not os.path.exists(TEST_PREDICTIONS_CSV):
        raise FileNotFoundError(f"Predictions CSV not found at: {TEST_PREDICTIONS_CSV}")

    samples = []
    with open(TEST_PREDICTIONS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            samples.append(r)

    print(f"Loaded {len(samples)} official PlantDoc test samples.")

    # 3. Analyze Baseline Preprocessing (Primary Analysis)
    print("\n[3/4] Generating Grad-CAM attributions for Baseline Preprocessing (Resize 256 + CenterCrop 224)...")
    baseline_tf = get_baseline_transform()
    cmap = matplotlib.colormaps["jet"]

    summary_rows = []
    per_sample_results = []

    for idx, s in enumerate(samples):
        img_path = s["filepath"]
        sample_id = s["sample_id"]
        filename = os.path.basename(img_path)
        gt_mapped = s["ground_truth_mapped"]
        gt_idx = LABEL_TO_IDX[gt_mapped]

        # Load & Preprocess
        img = Image.open(img_path).convert("RGB")
        input_tensor = baseline_tf(img).unsqueeze(0)
        img_rgb = denormalize_image(input_tensor)

        # Forward Pass
        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1)[0].numpy()

        pred_idx = int(probs.argmax())
        pred_label = IDX_TO_LABEL[pred_idx]
        confidence = float(probs[pred_idx])
        true_class_prob = float(probs[gt_idx])
        is_correct = (pred_label == gt_mapped)

        # Generate Grad-CAM for Predicted Class
        cam_pred = cam_engine.generate_cam(input_tensor, pred_idx)
        metrics_pred = compute_attribution_metrics(cam_pred)

        # Also Generate Grad-CAM for True Class if Misclassified
        cam_true = None
        metrics_true = None
        if not is_correct:
            cam_true = cam_engine.generate_cam(input_tensor, gt_idx)
            metrics_true = compute_attribution_metrics(cam_true)

        # Generate Overlay
        heatmap_rgba = cmap(cam_pred)
        heatmap_rgb = heatmap_rgba[:, :, :3]
        overlay_rgb = np.clip(0.6 * img_rgb + 0.4 * heatmap_rgb, 0.0, 1.0)

        # Save Heatmap & Overlay Standalone
        base_name = f"{sample_id}_{filename.replace('.jpg', '').replace('.JPG', '')}"
        heatmap_path = os.path.join(dirs["heatmaps"], f"{base_name}_heatmap.png")
        overlay_path = os.path.join(dirs["overlays"], f"{base_name}_overlay.png")
        fig_path = os.path.join(dirs["figures"], f"{base_name}_3panel.png")

        plt.imsave(heatmap_path, heatmap_rgb)
        plt.imsave(overlay_path, overlay_rgb)

        pred_short = pred_label.replace("Tomato___", "")
        save_visual_figure(
            original_rgb=img_rgb,
            heatmap=cam_pred,
            overlay_rgb=overlay_rgb,
            sample_id=sample_id,
            filename=filename,
            ground_truth=gt_mapped,
            pred_label=pred_label,
            confidence=confidence,
            true_prob=true_class_prob,
            cam_target_name=f"Predicted: {pred_short}",
            out_path=fig_path
        )

        # Label Review Flag for Known Questionable Scrapes
        label_flag = "VALID"
        if "canker" in filename.lower():
            label_flag = "QUESTIONABLE (Filename indicates Bacterial Canker)"
        elif "speck" in filename.lower():
            label_flag = "QUESTIONABLE (Filename indicates Bacterial Speck)"
        elif "%23" in filename or "common" in filename.lower() or "fig" in filename.lower():
            label_flag = "REVIEW (Scraped Publication Figure)"

        summary_rows.append({
            "sample_id": sample_id,
            "filename": filename,
            "ground_truth": gt_mapped,
            "predicted_class": pred_label,
            "confidence": round(confidence, 4),
            "true_class_prob": round(true_class_prob, 4),
            "is_correct": is_correct,
            "preprocessing": "Baseline Crop (256 -> 224)",
            "focus_region": metrics_pred["focus_region"],
            "peak_y": metrics_pred["peak_y"],
            "peak_x": metrics_pred["peak_x"],
            "is_peak_on_border": metrics_pred["is_peak_on_border"],
            "border_to_center_ratio": metrics_pred["border_to_center_ratio"],
            "label_quality_flag": label_flag,
            "figure_path": fig_path
        })

        per_sample_results.append({
            "sample_id": sample_id,
            "filename": filename,
            "ground_truth": gt_mapped,
            "predicted_class": pred_label,
            "confidence": confidence,
            "probabilities": {IDX_TO_LABEL[i]: float(probs[i]) for i in range(len(probs))},
            "is_correct": is_correct,
            "cam_metrics_predicted": metrics_pred,
            "cam_metrics_true_class": metrics_true,
            "label_quality_flag": label_flag,
            "artifacts": {
                "heatmap": heatmap_path,
                "overlay": overlay_path,
                "figure": fig_path
            }
        })

        # Save JSON per sample
        json_path = os.path.join(dirs["json"], f"{base_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(per_sample_results[-1], f, indent=2)

        print(f"  [{idx+1:02d}/28] {sample_id} ({filename}) -> Pred: {pred_short} (Conf: {confidence*100:.1f}%) | Focus: {metrics_pred['focus_region']}")

    # 4. Separate Analysis: Direct-Resize Condition for the 9 Bacterial Spot Samples
    print("\n[4/4] Generating Direct-Resize Attributions (Reported Separately for Bacterial Spot)...")
    direct_tf = get_direct_resize_transform()
    bact_samples = [s for s in samples if "Bacterial" in s["ground_truth_mapped"]]

    for idx, s in enumerate(bact_samples):
        img_path = s["filepath"]
        sample_id = s["sample_id"]
        filename = os.path.basename(img_path)
        gt_mapped = s["ground_truth_mapped"]
        gt_idx = LABEL_TO_IDX[gt_mapped]

        img = Image.open(img_path).convert("RGB")
        input_tensor = direct_tf(img).unsqueeze(0)
        img_rgb = denormalize_image(input_tensor)

        with torch.no_grad():
            outputs = model(input_tensor)
            probs = torch.softmax(outputs, dim=1)[0].numpy()

        pred_idx = int(probs.argmax())
        pred_label = IDX_TO_LABEL[pred_idx]
        confidence = float(probs[pred_idx])
        true_prob = float(probs[gt_idx])

        cam_pred = cam_engine.generate_cam(input_tensor, pred_idx)
        heatmap_rgba = cmap(cam_pred)
        heatmap_rgb = heatmap_rgba[:, :, :3]
        overlay_rgb = np.clip(0.6 * img_rgb + 0.4 * heatmap_rgb, 0.0, 1.0)

        base_name = f"direct_resize_{sample_id}_{filename.replace('.jpg', '').replace('.JPG', '')}"
        fig_path = os.path.join(dirs["direct_resize"], f"{base_name}_3panel.png")

        save_visual_figure(
            original_rgb=img_rgb,
            heatmap=cam_pred,
            overlay_rgb=overlay_rgb,
            sample_id=sample_id,
            filename=filename,
            ground_truth=gt_mapped,
            pred_label=pred_label,
            confidence=confidence,
            true_prob=true_prob,
            cam_target_name=f"DirectResize: {pred_label.replace('Tomato___', '')}",
            out_path=fig_path
        )

    # 5. Export Summary CSV
    csv_path = os.path.join(OUTPUT_BASE_DIR, "gradcam_summary.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "sample_id", "filename", "ground_truth", "predicted_class",
            "confidence", "true_class_prob", "is_correct", "preprocessing",
            "focus_region", "peak_y", "peak_x", "is_peak_on_border",
            "border_to_center_ratio", "label_quality_flag", "figure_path"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\nExported Grad-CAM Summary CSV to: {csv_path}")

    # Remove Hooks
    cam_engine.remove_hooks()
    print("Grad-CAM analysis completed successfully.")


if __name__ == "__main__":
    run_gradcam_analysis()

