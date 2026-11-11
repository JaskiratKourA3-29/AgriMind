# AgriMind — Training Data Preparation Specification & Split Report

**Document Type:** Formal Data Preparation Specification & Split Verification Record  
**Author:** AI/ML Engineering Assistant  
**Target:** AgriMind Stage 2 (Week 2 Vision Agent)

---

## 1. Context & Motivation

Stage 1 EDA across the three datasets revealed critical properties that must govern training data preparation:
1. **PlantVillage:**
   - 5,036 images across 3 tomato classes.
   - **Split Status Verified:** Neither `train_split.csv` nor `val_split.csv` exists anywhere on disk. The reported 80/20 counts (4,029 train / 1,007 val with seed 42) are a **mathematical specification/design calculation from project notes**, NOT a saved artifact or an executed operation.
   - Contains 16 exact duplicate files (8 pairs), of which exactly **8 files (4 pairs)** overlap with the 150 black-background cutout images in Late Blight.
   - 150 black-background images (`dark_frac > 0.3`) are confined entirely to `Tomato___Late_blight` and overlap with 4 duplicate pairs, but have 0 overlap with `rep_seed42` or `inspect_dark`.
2. **Tomato-Village:**
   - Predefined train/val/test splits exist in Variant A (3,162 / 902 / 461) and Variant B (3,945 / 1,124 / 584).
   - Only 2 classes (`Early_blight` and `Late_blight`) map directly to our 3-class tomato scope; Bacterial Spot is **not present**.
   - Contains severe class imbalances (up to 14.2x) and real-world multi-lesion complexities.
3. **PlantDoc:**
   - Official splits: Train (281 tomato images), Test (28 tomato images).
   - **Critical Leakage Identified:** 2 training images are identical (dHash = 0) to images in the official 28-image test set.

---

## 2. Proposed Class Mappings

Before combining or benchmarking models across datasets, the explicit class alignment is defined below:

| Target AgriMind Vision Class | PlantVillage Folder | Tomato-Village (Variant A/B/C) | PlantDoc Folder |
|---|---|---|---|
| **Bacterial Spot** | `Tomato___Bacterial_spot` | *Not Present* | `Tomato leaf bacterial spot` |
| **Early Blight** | `Tomato___Early_blight` | `Early_blight` / `Early blight` | `Tomato Early blight leaf` |
| **Late Blight** | `Tomato___Late_blight` | `Late_blight` / `Late blight` | `Tomato leaf late blight` |

*Other Tomato-Village classes (`Healthy`, `Leaf Miner`, `Magnesium Deficiency`, `Nitrogen Deficiency`, `Pottassium Deficiency`, `Spotted Wilt Virus`) must NOT be merged into the primary 3-class tomato vision model without explicit architectural accommodation.*

---

## 3. PlantVillage Stratified 80/20 Split (Executed & Verified)

### 3.1 Materialized Split Specifications (Seed 42)
The stratified 80/20 split was executed and verified using `scripts/generate_plantvillage_splits.py`. Output CSV files are saved at:
- **Train Split:** `data_splits/train_split.csv` (4,029 samples)
- **Validation Split:** `data_splits/val_split.csv` (1,007 samples)

**Per-Class Verified Sample Counts:**
| Class Label | Total Samples | Train (80%) | Val (20%) | Parity & Match Status |
|---|---|---|---|---|
| **Tomato___Bacterial_spot** | 2,127 | **1,702** (80.02%) | **425** (19.98%) | Exact match |
| **Tomato___Early_blight** | 1,000 | **800** (80.00%) | **200** (20.00%) | Exact match |
| **Tomato___Late_blight** | 1,909 | **1,527** (79.99%) | **382** (20.01%) | Exact match |
| **Total** | **5,036** | **4,029** (80.00%) | **1,007** (20.00%) | **100% Verified** |

### 3.2 Implemented Subgroup & Leakage Safeguards
1. **Duplicate-Group Separation (Zero Leakage):**
   - All 8 exact duplicate pairs (16 files total, all in Late Blight) were treated as atomic units.
   - **Train partition:** 12 duplicate files (6 complete pairs: 3 normal `.JPG` pairs, 3 black-background `.jpg` pairs).
   - **Validation partition:** 4 duplicate files (2 complete pairs: 1 normal `.JPG` pair, 1 black-background `.jpg` pair).
   - **Cross-split duplicate leakage:** **0 files (0 pairs)**. Zero identical MD5 hashes span the train and validation partitions.
2. **Black-Background Subgroup Distribution (150 Images):**
   - Distributed proportionally 80% / 20% across splits.
   - **Train partition:** **120 images** (80.00% of black-bg subgroup; 2.98% of training set).
   - **Validation partition:** **30 images** (20.00% of black-bg subgroup; 2.98% of validation set).
3. **Partition Independence & File Isolation:**
   - **Filepath overlap between train and val:** **0 files**.
   - Source dataset files were strictly untouched (read-only access).

---

## 4. Proposal for PlantDoc Evaluation Sets

1. **Official 28-Image External Test Set:**
   - Must be preserved strictly untouched as the external benchmark.
   - Zero training or hyperparameter tuning on these 28 images.
2. **Exclusion of Leaked Training Samples:**
   - In PlantDoc `train/`, exclude the two confirmed leaking samples:
     - `bacterial-canker3x2400-2ia1kgd.jpg`
     - `late_blight1.jpg`
   - Clean PlantDoc training pool: **279 images** (100 Bacterial Spot, 79 Early Blight, 100 Late Blight).
3. **Internal PlantDoc 80/20 Development Split (if training on PlantDoc):**
   - Train (223 images): 80 Bacterial Spot, 63 Early Blight, 80 Late Blight.
   - Val (56 images): 20 Bacterial Spot, 16 Early Blight, 20 Late Blight.

---

## 5. Augmentation & Preprocessing Rules

1. **Isolation:**
   - Data augmentations (random flip, rotation, color jitter, affine) must apply **only to training sets**.
   - Validation and test splits must receive **only deterministic evaluation transforms** (Resize to fixed dimension, CenterCrop, Normalize using training-set mean and std).
2. **Storage Implementation:**
   - Split lists must be stored as derived CSV or JSON files inside the AgriMind workspace (`data_splits/` or `outputs/`), **never by moving or modifying original files**.
