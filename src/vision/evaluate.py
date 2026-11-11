"""
Evaluation and diagnostic analysis utilities for AgriMind Vision Agent.
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, accuracy_score

CLASS_NAMES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight"
]
SHORT_NAMES = ["Bacterial_spot", "Early_blight", "Late_blight"]

def evaluate_model(model, dataloader, criterion, class_weights, device):
    """
    Evaluates model on validation dataloader.
    Computes overall loss, accuracy, Macro-F1, per-class metrics,
    and extracts subgroup metadata for black-background analysis.
    """
    model.eval()
    
    total_loss = 0.0
    total_weight = 0.0
    all_preds = []
    all_targets = []
    all_is_black_bg = []
    all_filepaths = []
    
    with torch.no_grad():
        for inputs, targets, metadata in dataloader:
            inputs = inputs.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            
            with torch.amp.autocast('cuda'):
                outputs = model(inputs)
                # Compute weighted batch loss
                w_batch = class_weights[targets]
                batch_w_sum = w_batch.sum().item()
                raw_loss = criterion(outputs, targets)
                
            total_loss += raw_loss.item() * batch_w_sum
            total_weight += batch_w_sum
            
            preds = torch.argmax(outputs, dim=1).cpu().numpy()
            all_preds.extend(preds)
            all_targets.extend(targets.cpu().numpy())
            if isinstance(metadata["is_black_bg"], torch.Tensor):
                all_is_black_bg.extend(metadata["is_black_bg"].cpu().numpy().tolist())
            else:
                all_is_black_bg.extend(metadata["is_black_bg"])
            all_filepaths.extend(metadata["filepath"])
            
    val_loss = total_loss / total_weight if total_weight > 0 else 0.0
    
    all_preds = np.array(all_preds, dtype=int)
    all_targets = np.array(all_targets, dtype=int)
    all_is_black_bg = np.array(all_is_black_bg, dtype=bool)
    
    # Core Metrics
    accuracy = float(accuracy_score(all_targets, all_preds))
    p_class, r_class, f1_class, support_class = precision_recall_fscore_support(
        all_targets, all_preds, labels=[0, 1, 2], zero_division=0
    )
    macro_f1 = float(np.mean(f1_class))
    _, _, weighted_f1, _ = precision_recall_fscore_support(
        all_targets, all_preds, average='weighted', zero_division=0
    )
    
    cm = confusion_matrix(all_targets, all_preds, labels=[0, 1, 2])
    
    metrics = {
        "val_loss": round(val_loss, 4),
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "weighted_f1": round(float(weighted_f1), 4),
        "per_class": {
            SHORT_NAMES[i]: {
                "precision": round(float(p_class[i]), 4),
                "recall": round(float(r_class[i]), 4),
                "f1_score": round(float(f1_class[i]), 4),
                "support": int(support_class[i]),
            }
            for i in range(3)
        },
        "confusion_matrix": cm.tolist(),
        "class_order": SHORT_NAMES,
    }
    
    # Subgroup Evaluation: Black-bg (n=30) vs Normal (n=977)
    subgroup_metrics = compute_subgroup_diagnostics(all_targets, all_preds, all_is_black_bg)
    
    return metrics, subgroup_metrics, all_preds, all_targets

def compute_subgroup_diagnostics(targets, preds, is_black_bg):
    """
    Evaluates performance separately on black-background images vs normal images.
    """
    diagnostics = {}
    
    for grp_name, mask in [("black_background", is_black_bg), ("normal_background", ~is_black_bg)]:
        grp_targets = targets[mask]
        grp_preds = preds[mask]
        n_samples = int(len(grp_targets))
        
        if n_samples == 0:
            diagnostics[grp_name] = {"count": 0}
            continue
            
        acc = float(accuracy_score(grp_targets, grp_preds))
        # Unique classes present in subgroup
        classes_present = np.unique(grp_targets).tolist()
        cm_sub = confusion_matrix(grp_targets, grp_preds, labels=[0, 1, 2]).tolist()
        
        diagnostics[grp_name] = {
            "count": n_samples,
            "accuracy": round(acc, 4),
            "classes_present": [SHORT_NAMES[c] for c in classes_present],
            "confusion_matrix": cm_sub,
        }
        
    return diagnostics

def plot_confusion_matrix(cm, class_names, output_path):
    """
    Plots and saves formatted confusion matrix.
    """
    fig, ax = plt.subplots(figsize=(6, 5))
    im = ax.imshow(cm, interpolation='nearest', cmap=plt.cm.Blues)
    ax.figure.colorbar(im, ax=ax)
    
    ax.set(
        xticks=np.arange(cm.shape[1]),
        yticks=np.arange(cm.shape[0]),
        xticklabels=class_names,
        yticklabels=class_names,
        ylabel='True Label',
        xlabel='Predicted Label',
        title='PlantVillage 3-Class Confusion Matrix'
    )
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    
    thresh = cm.max() / 2.
    for i in range(cm.shape[0]):
        for j in range(cm.shape[1]):
            ax.text(
                j, i, format(cm[i, j], 'd'),
                ha="center", va="center",
                color="white" if cm[i, j] > thresh else "black",
                fontsize=11, fontweight="bold"
            )
            
    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Confusion matrix saved to: {output_path}")
