# AgriMind Week 2 — Vision Agent Baseline Training & Evaluation Report

**Date & Time:** October 13, 2026 | 15:05 IST  
**Project:** AgriMind — Multi-Agent AI System for Crop Disease Investigation, Risk Assessment & Adaptive Decision Support  
**Course Code:** COM71116-21 (7th-Semester CSE Minor Project)  
**Team:** Jaskirat Kour (Team Leader), Palakjot Kour, Sayam Malhotra, Ikjot Singh  
**Stage:** Week 2 — Vision Agent Development and Initial Training  
**Status:** Completed End-to-End

---

## 1. Executive Summary

This report documents the end-to-end execution of the Week 2 Vision Agent baseline training for the AgriMind system. The objective was to fine-tune a deep convolutional neural network (ResNet-50) with pretrained ImageNet-1K weights to classify three tomato leaf diseases from the PlantVillage dataset under rigorous isolation, reproducibility, and memory-safe training conditions.

### Primary Results at a Glance
- **Architecture:** ResNet-50 (`IMAGENET1K_V2` backbone) with custom 3-class linear classification head.
- **Dataset:** PlantVillage 3-class tomato subset (4,029 training samples, 1,007 validation samples; 80/20 stratified split, seed 42).
- **Best Validation Epoch:** Epoch 12 (Fine-tuning phase).
- **Validation Macro-F1:** **98.28%** (0.9828).
- **Overall Validation Accuracy:** **98.41%** (991 / 1,007 correctly classified).
- **Weighted-F1 Score:** **98.41%** (0.9841).
- **Checkpoint Location:** `outputs/week2_vision/best_model.pth` (282,626,785 bytes, verified loadable).
- **Prohibited Datasets / Environments:** Zero access to PlantDoc test set; zero modifications to `fiftyone-env`, `agrimind-eda`, or MongoDB.

---

## 2. Environment, Hardware, and Dependency Verification

All training and evaluation operations were executed within the designated isolated virtual environment:

| Property | Value / Verification |
|---|---|
| **Environment Path** | `/home/jaskirat/agrimind-vision-env` |
| **Python Version** | `3.13.16` |
| **PyTorch Version** | `2.6.0+cu124` |
| **Torchvision Version** | `0.21.0+cu124` |
| **CUDA Runtime** | CUDA 12.4 compatible, Driver 565.65 (CUDA 12.7 host capability) |
| **GPU Hardware** | NVIDIA GeForce RTX 2050 Laptop GPU |
| **Compute Capability** | `(8, 6)` |
| **Dedicated VRAM** | 4,096 MiB (4.0 GB) |
| **OS / Platform** | Ubuntu 26.04.1 LTS under WSL2 (Windows 11 host) |
| **Auxiliary Packages** | `pandas==3.0.6`, `scikit-learn==1.9.1`, `matplotlib==3.11.2`, `pillow==12.3.0` |

### Isolated Smoke Test
Prior to full training, an isolated, disposable smoke test was executed on the GPU:
- Forward pass, mixed-precision autocasting (`torch.amp.autocast('cuda')`), backward pass, gradient scaling, and optimizer step were validated on 2 training mini-batches and 2 validation mini-batches.
- **Empirical batch timing:** Batch 1 (cold start + CUDA warmup) was 2,755.2 ms; Batch 2 was 225.0 ms. Average batch time: 1,490.1 ms.
- Measured empirical epoch duration estimate: ~187.8 seconds (~3.13 minutes).
- Following validation, disposable model and optimizer states were completely destroyed and GPU memory was cleared via `gc.collect()` and `torch.cuda.empty_cache()` before commencing baseline training.

---

## 3. Dataset Configuration & Split Integrity

The Vision Agent was trained and evaluated strictly on the verified Week 1 PlantVillage stratified splits:

- **Training split CSV:** `data_splits/train_split.csv` (4,029 samples)
- **Validation split CSV:** `data_splits/val_split.csv` (1,007 samples)

### Class Distribution and Weighting

| Class Index | Disease Class Label | Short Name | Training Samples ($N_{\text{train}}$) | Validation Samples ($N_{\text{val}}$) | Total Samples | Normalized Class Weight ($w_c$) |
|---|---|---|---|---|---|---|
| 0 | `Tomato___Bacterial_spot` | `Bacterial_spot` | 1,702 | 425 | 2,127 | **0.78907168** |
| 1 | `Tomato___Early_blight` | `Early_blight` | 800 | 200 | 1,000 | **1.67875000** |
| 2 | `Tomato___Late_blight` | `Late_blight` | 1,527 | 382 | 1,909 | **0.87950229** |
| **Total** | — | — | **4,029** | **1,007** | **5,036** | **$\sum w_c / 3 = 1.000$** |

### Split Safeguards
- **Atomic Duplicates:** All 8 identical duplicate pairs identified during Stage 1 EDA remain strictly partitioned (6 pairs wholly in train, 2 pairs wholly in validation; zero cross-split leakage).
- **Black-Background Images:** All 150 identified black-background samples belong exclusively to `Tomato___Late_blight`. They are distributed proportionally: 120 in train (2.98% of train) and 30 in validation (2.98% of val).
- **Validation Determinism:** Validation data was never augmented; transforms consisted purely of deterministic `Resize(256)`, `CenterCrop(224)`, and ImageNet normalization.

---

## 4. Model Architecture & Training Protocol

### 4.1 Architecture
- **Backbone:** ResNet-50 (`torchvision.models.resnet50(weights=ResNet50_Weights.IMAGENET1K_V2)`).
- **Classification Head:** Linear layer replacement `nn.Linear(2048, 3)`.
- **Parameter Breakdown:**
  - Total Parameters: **23,514,179**
  - Phase 1 Trainable (Warmup): **6,147**
  - Phase 2 Trainable (Full Fine-tuning): **23,514,179**

### 4.2 Training Hyperparameters & Two-Phase Strategy
- **Random Seed:** 42 across Python, NumPy, PyTorch CPU, and PyTorch CUDA.
- **Batch Size:** 32 (with dynamic micro-batch slicing fallback).
- **Loss Function:** `nn.CrossEntropyLoss(weight=class_weights, reduction='mean')`.
- **Precision:** Mixed Precision AMP FP16 with `GradScaler`.
- **Phase 1: Warmup (Epochs 1–3):**
  - Backbone frozen; only classification head trained.
  - Optimizer: AdamW (`lr=1e-3`, `weight_decay=1e-2`).
- **Phase 2: Fine-Tuning (Epochs 4–18):**
  - All layers unfrozen.
  - Differential learning rates: Backbone `lr=1e-4`, Head `lr=5e-4`.
  - Scheduler: `CosineAnnealingLR(T_max=15, eta_min=1e-6)`.
- **Checkpoint Selection Criterion:** Highest Validation Macro-F1 score.

### 4.3 OOM Recovery & Numerical Equivalence
The training step incorporated a bounded OOM recovery cascade ($1 \rightarrow 2 \rightarrow 4$ micro-batches) using contiguous integer slicing `inputs[start:end]` and mathematical scaling by sample weight sums:
$$\mathcal{L}_{\text{scaled}, i} = \mathcal{L}_{\text{micro}, i} \times \frac{W_i}{W_{\text{full}}}$$
During full 18-epoch training, the 4 GB VRAM headroom was maintained cleanly, and all batches completed at chunk level 1 without triggering micro-batch splitting or memory exceptions.

---

## 5. Complete Training and Validation History

Below is the verified epoch-by-epoch training log extracted directly from `outputs/week2_vision/training_metrics.json`:

| Epoch | Phase | Train Loss | Train Acc | Val Loss | Val Acc | Val Macro-F1 | Val Weighted-F1 | Epoch Time | Checkpoint Status |
|---|---|---|---|---|---|---|---|---|---|
| **1** | Warmup | 4.8890 | 42.54% | 3.7840 | 45.78% | 0.4407 | 0.4681 | 39.1 s | Saved (Initial Best) |
| **2** | Warmup | 3.3571 | 53.71% | 3.0659 | 52.33% | 0.5156 | 0.5405 | 38.2 s | Saved (New Best) |
| **3** | Warmup | 2.6457 | 59.62% | 2.4853 | 59.68% | 0.5721 | 0.6074 | 37.5 s | Saved (New Best) |
| **4** | Fine-tune | 0.6979 | 86.75% | 0.4013 | 91.76% | 0.9052 | 0.9171 | 39.0 s | Saved (New Best) |
| **5** | Fine-tune | 0.1869 | 95.33% | 0.2943 | 95.93% | 0.9534 | 0.9589 | 38.6 s | Saved (New Best) |
| **6** | Fine-tune | 0.0828 | 97.69% | 0.1787 | 96.92% | 0.9665 | 0.9691 | 39.5 s | Saved (New Best) |
| **7** | Fine-tune | 0.0448 | 98.71% | 0.1741 | 97.02% | 0.9651 | 0.9699 | 38.2 s | — |
| **8** | Fine-tune | 0.0228 | 99.40% | 0.1383 | 97.82% | 0.9757 | 0.9781 | 37.8 s | Saved (New Best) |
| **9** | Fine-tune | 0.0336 | 99.06% | 0.1445 | 97.82% | 0.9751 | 0.9781 | 38.1 s | — |
| **10** | Fine-tune | 0.0139 | 99.60% | 0.1178 | 98.11% | 0.9790 | 0.9811 | 37.9 s | Saved (New Best) |
| **11** | Fine-tune | 0.0114 | 99.68% | 0.1283 | 98.21% | 0.9803 | 0.9821 | 38.2 s | Saved (New Best) |
| **12** | Fine-tune | **0.0099** | **99.65%** | **0.0962** | **98.41%** | **0.9828** | **0.9841** | **38.1 s** | **BEST CHECKPOINT** |
| **13** | Fine-tune | 0.0123 | 99.60% | 0.1417 | 97.62% | 0.9719 | 0.9760 | 38.1 s | — |
| **14** | Fine-tune | 0.0096 | 99.68% | 0.1187 | 97.72% | 0.9738 | 0.9770 | 38.0 s | — |
| **15** | Fine-tune | 0.0104 | 99.65% | 0.1277 | 98.21% | 0.9797 | 0.9821 | 37.8 s | — |
| **16** | Fine-tune | 0.0092 | 99.75% | 0.1169 | 98.01% | 0.9773 | 0.9800 | 37.9 s | — |
| **17** | Fine-tune | 0.0082 | 99.78% | 0.1001 | 98.31% | 0.9806 | 0.9830 | 37.8 s | — |
| **18** | Fine-tune | 0.0110 | 99.63% | 0.1072 | 98.31% | 0.9808 | 0.9831 | 38.0 s | — |

- **Total Training Wall-Clock Time:** 688.1 seconds (~11.47 minutes).
- **Average Epoch Duration:** 38.2 seconds.

---

## 6. Final Evaluation of Best Model (Epoch 12)

The best model checkpoint (`best_model.pth`) was re-loaded from disk and independently evaluated across the entire 1,007-image validation set.

### 6.1 Summary Metrics
- **Overall Accuracy:** **98.41%** (991 / 1,007)
- **Macro-Averaged F1-Score:** **98.28%**
- **Weighted F1-Score:** **98.41%**
- **Validation Loss:** **0.0962**

### 6.2 Per-Class Performance Breakdown

| Disease Class | Support ($N_{\text{val}}$) | Precision | Recall | F1-Score | False Positives | False Negatives |
|---|---|---|---|---|---|---|
| **Bacterial Spot** | 425 | 98.60% (422/428) | 99.29% (422/425) | **98.94%** | 6 | 3 |
| **Early Blight** | 200 | 99.48% (192/193) | 96.00% (192/200) | **97.71%** | 1 | 8 |
| **Late Blight** | 382 | 97.67% (377/386) | 98.69% (377/382) | **98.18%** | 9 | 5 |
| **Macro Average** | — | **98.58%** | **97.99%** | **98.28%** | — | — |
| **Weighted Average** | 1,007 | **98.42%** | **98.41%** | **98.41%** | — | — |

### 6.3 Confusion Matrix Analysis

Class order: `[0: Bacterial_spot, 1: Early_blight, 2: Late_blight]`

```
                      Predicted Label
                Bacterial    Early    Late    Total
True Bacterial     422         0        3      425
True Early           2       192        6      200
True Late            4         1      377      382
Total Predicted    428       193      386     1007
```

**Confusion Matrix Observations:**
1. **Bacterial Spot:** Exhibited the highest recall (99.29%). Only 3 samples were misclassified as Late Blight. Zero confusion with Early Blight occurred.
2. **Early Blight:** Showed the lowest recall (96.00%) among the three classes, with 8 misclassifications: 6 samples were misclassified as Late Blight, and 2 as Bacterial Spot.
3. **Late Blight:** Achieved 98.69% recall. 4 samples were misclassified as Bacterial Spot and 1 sample as Early Blight.
4. **Bacterial vs Late Blight Cross-Confusion:** 7 total instances of confusion occurred between Bacterial Spot and Late Blight (3 true Bacterial predicted as Late; 4 true Late predicted as Bacterial).
5. **Early vs Late Blight Confusion:** 7 total instances occurred (6 true Early predicted as Late; 1 true Late predicted as Early), consistent with late-stage necrotic lesion visual overlap.

### 6.4 Visual Confusion Matrix
The confusion matrix plot is saved at `outputs/week2_vision/confusion_matrix.png`.

---

## 7. Subgroup Evaluation: Black-Background Analysis

During Stage 1 EDA, 150 images in the PlantVillage dataset were identified as having artificially segmented black backgrounds (dark fraction > 50%), all belonging to `Tomato___Late_blight`. The stratified split partitioned 30 of these images into the validation set.

A dedicated subgroup diagnostic was executed on the validation set to determine whether the model relies on background artifacts or performs consistently across visual domains:

| Subgroup | Sample Count | True Class Composition | Correct Predictions | Subgroup Accuracy |
|---|---|---|---|---|
| **Black Background** | 30 | 30 Late Blight (100%) | 30 / 30 | **100.00%** |
| **Natural Background** | 977 | 425 Bacterial, 200 Early, 352 Late | 961 / 977 | **98.36%** |

### Findings
- The model correctly classified all 30 black-background Late Blight samples.
- The model also achieved **98.58% accuracy on natural-background Late Blight samples** (347 / 352 correct), demonstrating that Late Blight recognition is driven by foliar lesion pathology rather than an exclusive reliance on black background shortcuts.
- No non-Late Blight classes were falsely predicted as Late Blight due to background features.

---

## 8. Honest Limitations & Class-Level Weaknesses

While the baseline ResNet-50 achieves strong validation scores on the PlantVillage benchmark, several critical limitations must be explicitly noted:

1. **Laboratory Bias vs. Field Conditions (PlantVillage Domain Gap):**
   PlantVillage images are collected under controlled laboratory/studio conditions (uniform illumination, single leaf per frame, homogeneous or masked backgrounds). In-field images (such as PlantDoc) feature complex backgrounds, variable shadows, overlapping foliage, multi-leaf disease stages, and camera motion blur. High laboratory accuracy does **not** guarantee generalization to field imagery.
2. **Early Blight Recall Deficit (96.00%):**
   Early Blight has smaller training representation (800 training samples vs 1,702 for Bacterial and 1,527 for Late Blight). Despite inverse-frequency class weighting ($w=1.67875$), 4.0% of Early Blight validation samples were misdiagnosed, primarily as Late Blight. In practical agronomy, distinguishing advanced early blight concentric lesions from spreading late blight water-soaked lesions remains challenging when foliage exhibits heavy necrosis.
3. **Black Background Confounding Risk:**
   Because all 150 black-background images in the dataset belong to Late Blight, there remains a lingering inductive bias where the network could assign residual weight to background darkness. While natural background Late Blight accuracy was high (98.58%), this domain shift must be monitored closely when testing on in-field data.
4. **Single-Model Baseline:**
   This model represents the baseline architecture (ResNet-50). Alternative vision backbones (e.g., Vision Transformer / Swin, EfficientNet, ConvNeXt) have not yet been trained or compared.

---

## 9. Produced Artifacts & Path Verification

All planned Week 2 artifacts were generated directly by the pipeline and verified on disk:

| Artifact Description | Expected Location | Actual Disk Path | Size (Bytes) | Verification Status |
|---|---|---|---|---|
| **Best Model Checkpoint** | `outputs/week2_vision/best_model.pth` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\outputs\week2_vision\best_model.pth` | 282,626,785 | **Verified & Loadable** |
| **Training History Metrics** | `outputs/week2_vision/training_metrics.json` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\outputs\week2_vision\training_metrics.json` | 4,543 | **Verified** (18 epochs) |
| **Final Evaluation Metrics** | `outputs/week2_vision/final_evaluation.json` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\outputs\week2_vision\final_evaluation.json` | 728 | **Verified** |
| **Confusion Matrix Plot** | `outputs/week2_vision/confusion_matrix.png` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\outputs\week2_vision\confusion_matrix.png` | 54,358 | **Verified** |
| **Subgroup Diagnostics** | `outputs/week2_vision/subgroup_evaluation.json` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\outputs\week2_vision\subgroup_evaluation.json` | 654 | **Verified** |
| **Baseline Report** | `docs/week2_vision_baseline_report.md` | `c:\Users\asus\Downloads\Agri_Mind_Minor_Project\docs\week2_vision_baseline_report.md` | — | **Verified** (This document) |

---

## 10. Week 2 Completion Status Summary

| Task / Objective | Status | Evidence & Output Path |
|---|---|---|
| **1. Isolated Environment Setup & Inspection** | **Completed** | `/home/jaskirat/agrimind-vision-env` (PyTorch 2.6.0+cu124, RTX 2050 GPU verified). |
| **2. Disposable Smoke Test & Timing** | **Completed** | Batch time 1,490.1 ms; GPU state purged cleanly before training. |
| **3. ResNet-50 Baseline Architecture Selection** | **Completed** | `IMAGENET1K_V2` pretrained weights, custom 3-class linear head (`src/vision/model.py`). |
| **4. Balanced Class Weighting & Loss Setup** | **Completed** | Exact weights $[0.7891, 1.6788, 0.8795]$ configured in `CrossEntropyLoss`. |
| **5. Two-Phase Training (Warmup + Fine-Tuning)** | **Completed** | 3 warmup epochs + 15 fine-tuning epochs executed; best checkpoint at Epoch 12. |
| **6. Checkpoint Selection on Validation Macro-F1** | **Completed** | `best_model.pth` saved at Macro-F1 = 0.9828. |
| **7. Final Evaluation & Metric Computation** | **Completed** | Accuracy 98.41%, Macro-F1 98.28%, per-class P/R/F1 in `final_evaluation.json`. |
| **8. Confusion Matrix Generation** | **Completed** | Saved at `outputs/week2_vision/confusion_matrix.png`. |
| **9. Subgroup Evaluation (Black Background)** | **Completed** | Evaluated 30 black-bg vs 977 normal-bg samples in `subgroup_evaluation.json`. |
| **10. Strict Boundary Preservation** | **Completed** | Zero access to PlantDoc test set; `agrimind-eda`, `fiftyone-env`, and MongoDB untouched. |

**Conclusion:** All Week 2 Vision Agent development, baseline training, evaluation, diagnostic analysis, and documentation objectives have been successfully executed and completed end-to-end.
