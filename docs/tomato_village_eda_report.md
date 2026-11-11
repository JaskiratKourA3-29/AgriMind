# Tomato-Village EDA — Comprehensive Multi-Variant Report

**Dataset:** Tomato-Village Dataset  
**Source Path:** `/home/jaskirat/datasets/Tomato-Village`  
**Paper Citation:** Gehlot, M., Saxena, R.K. & Gandhi, G.C. “Tomato-Village”: a dataset for end-to-end tomato disease detection in a real-world environment. *Multimedia Systems* (2023).  
**Geographic Origin (from Paper/README):** Field observations from Jodhpur and Jaipur districts, Rajasthan, India. (Do not extend to other datasets).  
**Verification Method:** Independent calculation via `scripts/eda_tomato_village_variant_a.py`, `scripts/eda_tomato_village_variant_b.py`, `scripts/eda_tomato_village_variant_c.py`.

---

## 1. Variant A (Multiclass Classification)

### 1.1 Class Inventory across Predefined Splits
Found **4,526 total files**, of which **4,525 are valid JPEG images** and **1 is an invalid non-image OS artifact** (`train/Magnesium Deficiency/desktop.ini`, size 68 bytes).

| Class Name (Native Spelling) | Train | Val | Test | Total Images | % of Total | Imbalance vs Min Class |
|---|---|---|---|---|---|---|
| **Early_blight** | 347 | 99 | 50 | **496** | 10.96% | 6.89x |
| **Healthy** | 151 | 43 | 22 | **216** | 4.77% | 3.00x |
| **Late_blight** | 632 | 180 | 92 | **904** | 19.98% | 12.56x |
| **Leaf Miner** | 716 | 204 | 104 | **1,024** | 22.63% | **14.22x (Max)** |
| **Magnesium Deficiency** | 654* | 187 | 95 | **936** | 20.68% | 13.00x |
| **Nitrogen Deficiency** | 251 | 72 | 37 | **360** | 7.96% | 5.00x |
| **Pottassium Deficiency** | 50 | 14 | 8 | **72** | 1.59% | **1.00x (Min)** |
| **Spotted Wilt Virus** | 361 | 103 | 53 | **517** | 11.43% | 7.18x |
| **Total Images** | **3,162** | **902** | **461** | **4,525** | 100.00% | Max/Min Ratio: **14.22x** |

*\*Note: `train/Magnesium Deficiency/` has 655 files, but 1 is `desktop.ini`.*

### 1.2 Image Specifications & Quality
- **Dimensions:** 100% of images are exactly **256x256** (single distinct dimension pair).
- **Color Format:** 100% **JPEG**, color mode **RGB** (3 channels).
- **Integrity Failures:** 0 among image files (only `desktop.ini` failed as expected).
- **Exact Duplicates (MD5):** **0 duplicates** across all 4,525 images! Zero duplicates within or across classes/splits.

### 1.3 Brightness, Contrast & Dark Fraction
- **Brightness Mean:** 146.6 to 153.9 across all classes (overall mean ~149.8), significantly brighter than PlantVillage lab images (mean ~110).
- **Contrast Mean:** 37.5 to 49.8 across classes.
- **Dark Fraction (`dark_frac > 0.3`):** **0 images** (0.00%). Max `dark_frac` is 0.26. There are NO artificial black background cutouts in Tomato-Village.

---

## 2. Variant B (Multilabel Classification)

### 2.1 File & Annotation Summary
- **Annotation Source:** `Multi-Label dataset - with augmented.csv` (size 364,310 bytes).
- **Total Records:** **5,653 rows** matching **5,653 images on disk** across `train/` (3,945), `val/` (1,124), `test/` (584).
- **Disk Files vs CSV:** 100% match. (Note: 3 non-image `desktop.ini` files exist, one in each split folder).
- **Labels Considered (8):** Early blight, Healthy, Late blight, Leaf Miner, Magnesium Deficiency, Nitrogen Deficiency, Pottassium Deficiency, Spotted Wilt Virus.
- **Mismatches with CSV 'SUM' column:** **0**.

### 2.2 Label Distribution & Multilabel Breakdown
- **Single-Label Images:** **4,525 images (80.05%)** — exactly identical in count to the 4,525 base images in Variant A!
- **Multi-Label Images:** **1,128 images (19.95%)**:
  - 2 labels: **1,106 images (19.56%)**
  - 3 labels: **22 images (0.39%)**
  - 0 labels: **0 images (0.00%)**

### 2.3 Label Frequencies across 5,653 Samples
1. Leaf Miner: **2,101 (37.17%)**
2. Magnesium Deficiency: **1,518 (26.85%)**
3. Late blight: **918 (16.24%)**
4. Spotted Wilt Virus: **917 (16.22%)**
5. Early blight: **579 (10.24%)**
6. Nitrogen Deficiency: **469 (8.30%)**
7. Healthy: **216 (3.82%)**
8. Pottassium Deficiency: **85 (1.50%)**

### 2.4 Label Co-occurrence & Relationships
- **Healthy Leaves:** Purely single-label; **0 co-occurrences** with any disease.
- **Dominant Co-occurring Disease:** **Leaf Miner** is present in nearly all multilabel images:
  - Leaf Miner + Magnesium Deficiency: **543 co-occurrences** (521 as a pairwise combination)
  - Leaf Miner + Spotted Wilt Virus: **386 co-occurrences** (375 pairwise)
  - Leaf Miner + Nitrogen Deficiency: **97 co-occurrences**
  - Leaf Miner + Early blight: **46 co-occurrences**
  - Leaf Miner + Late blight: **14 co-occurrences**
  - Leaf Miner + Pottassium Deficiency: **13 co-occurrences**

---

## 3. Variant C (Object Detection)

### 3.1 Dataset Inventory & Consistency
- **Train Split:** **11,493 images**, **11,493 YOLO txt files**, **11,493 Pascal VOC XML files**.
- **Val Split:** **2,875 images**, **2,875 YOLO txt files**, **2,875 Pascal VOC XML files**.
- **Total Images:** **14,368 images** (80.00% train, 20.00% val).
- **YOLO vs VOC Consistency:** **0 box count mismatches** across all 14,368 image pairs. 100% structural consistency!

### 3.2 Annotation Formatting & Data Hygiene Findings
- **Class ID Representation:** Class IDs in YOLO text files and VOC XML `<name>` tags are stored as float strings (e.g., `3.0` instead of `3`).
- **Empty YOLO Files (0 annotations):** 90 in train (0.78%), 19 in val (0.66%).
- **Invalid Class IDs:** **0**. (All values map to `{0..7}`).
- **Out-of-Range Coordinates:** **0**. (All coordinates strictly in `[0.0, 1.0]`).

### 3.3 Bounding Box & Class Frequencies
Total annotated boxes across dataset: **161,223 bounding boxes** (Train: 128,317; Val: 32,906).

| Class ID | Class Name | Train Boxes | % Train | Val Boxes | % Val | Total Boxes |
|---|---|---|---|---|---|---|
| **0** | **Early_blight** | 0 | 0.00% | 0 | 0.00% | **0** |
| **1** | **Healthy** | 0 | 0.00% | 0 | 0.00% | **0** |
| **2** | **Late_blight** | 3,174 | 2.47% | 764 | 2.32% | **3,938** |
| **3** | **Leaf Miner** | 85,209 | 66.41% | 21,990 | 66.83% | **107,199** |
| **4** | **Magnesium Deficiency** | 12,503 | 9.74% | 3,367 | 10.23% | **15,870** |
| **5** | **Nitrogen Deficiency** | 1,310 | 1.02% | 383 | 1.16% | **1,693** |
| **6** | **Pottassium Deficiency** | 869 | 0.68% | 257 | 0.78% | **1,126** |
| **7** | **Spotted Wilt Virus** | 25,252 | 19.68% | 6,145 | 18.67% | **31,397** |

> [!IMPORTANT]
> **Key Detection Scope Finding:** Variant C contains **zero bounding boxes for Early Blight or Healthy**. Diseases in Variant C are heavily concentrated on **Leaf Miner (66.5%)** and **Spotted Wilt Virus (19.5%)**.

### 3.4 Bounding Box Geometry & Density
- **Object Density:** Over **96% of images contain multiple bounding boxes** (96.21% in train, 96.45% in val).
- **Mean objects per image:** **11.16** in train, **11.45** in val. Max objects in a single image: **106**.
- **Normalized Box Width / Height:** Mean width = **0.119**, mean height = **0.115** (~12% of image dimension).
- **Normalized Box Area:** Mean area = **0.0194** (< 2% of image area), median area = **0.0078** (< 1% of image area). Bounding boxes represent fine, localized leaf symptoms (insect trails, spots) rather than whole plants.
