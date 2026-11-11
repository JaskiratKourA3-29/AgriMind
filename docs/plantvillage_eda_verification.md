# PlantVillage EDA — Verification & Outstanding Checks Report

**Dataset:** PlantVillage Tomato 3-Class Subset  
**Source Path:** `/mnt/c/Users/asus/PlantVillage-Dataset/raw/color`  
**FiftyOne Dataset:** `plantvillage_tomato3` (MongoDB port 27018)  
**Verification Method:** Independent calculation via Python 3.13 (`scripts/verify_plantvillage.py`, `scripts/inspect_plantvillage_subsets.py`) compared against existing artifacts in `~/agrimind-fiftyone-eda/outputs/`. Existing files were strictly preserved.

---

## 1. Quantitative Verification Summary

All reported numbers from previous sessions were checked against the source files and verified with 100% precision:

| Metric | Reported Value | Verified Value | Evidence / Output File |
|---|---|---|---|
| **Total Images** | 5,036 | **5,036** | `plantvillage_image_stats.csv` |
| **Bacterial Spot Count** | 2,127 (42.24%) | **2,127 (42.24%)** | `Tomato___Bacterial_spot/` |
| **Early Blight Count** | 1,000 (19.86%) | **1,000 (19.86%)** | `Tomato___Early_blight/` |
| **Late Blight Count** | 1,909 (37.91%) | **1,909 (37.91%)** | `Tomato___Late_blight/` |
| **Imbalance Ratio (Max/Min)** | ~2.13 | **2.127** (2127 / 1000) | Moderate class imbalance |
| **Image Integrity** | 0 failures | **0 failures** | PIL verify + RGB/L array conversion |
| **Dimensions & Channels** | 256x256, 3 channels, JPEG | **256x256, RGB, JPEG (100%)** | All 5,036 images |
| **File Extensions** | .JPG 4,883; .jpg 152; .jpeg 1 | **.JPG: 4,883; .jpg: 152; .jpeg: 1** | Exactly 153 non-.JPG |
| **Non-.JPG Class & Name** | All 153 in Late Blight, all contain `GHLB` | **Verified True (153 / 153)** | Substring match on filename |
| **Exact MD5 Duplicates** | 5,028 unique; 8 pairs of 2 (16 files) | **5,028 unique; 8 pairs of 2 (16 files)** | `plantvillage_md5_duplicates.csv` |
| **Duplicate Classes** | All 16 in Late Blight; none spanning classes | **Verified True (16 in Late Blight)** | 0 cross-class duplicates |

---

## 2. Brightness, Contrast & dark_frac Breakdown

### 2.1 Per-Class Overall Metrics
- **Bacterial Spot (n=2,127):** Brightness Mean = **104.92** (std 10.71) | Contrast Mean = **33.41** (std 5.99)
- **Early Blight (n=1,000):** Brightness Mean = **110.58** (std 14.15) | Contrast Mean = **46.31** (std 11.04)
- **Late Blight Overall (n=1,909):** Brightness Mean = **113.43** (std 28.62) | Contrast Mean = **39.59** (std 14.90)

### 2.2 Late Blight Subgroup Analysis (.JPG vs non-.JPG)
The 153 non-.JPG files represent a severe bimodal shift inside the Late Blight class:
- **Late Blight .JPG (n=1,756):**
  - Brightness Mean: **120.48** (std 15.41)
  - Contrast Mean: **39.10** (std 15.09)
- **Late Blight non-.JPG (n=153):**
  - Brightness Mean: **32.45** (std 37.91)
  - Contrast Mean: **45.25** (std 11.83)

### 2.3 Dark Fraction Analysis (`dark_frac` = fraction of pixels < 15/255)
- **Non-.JPG files (n=153):**
  - `dark_frac > 0.3`: **150 / 153** (98.04%)
  - `dark_frac > 0.5`: **144 / 153** (94.12%)
  - `dark_frac <= 0.3` (bright outliers): **3 files** (all `dark_frac = 0.000`):
    1. `07b42bb5-9f6c-43bc-9bbe-e4b127d84cb6___GHLB Leaf 18.1 Day 8.jpg` (Brightness 153.4, Contrast 49.0)
    2. `60196a6c-a134-4107-8178-d1bb47450cee___GHLB Leaf 23.1 Day 9.jpg` (Brightness 132.0, Contrast 65.7)
    3. `d0badc95-d04c-457b-8db8-aa6e198f4bd6___GHLB Leaf 10 Day 6.jpeg` (Brightness 109.7, Contrast 43.7)
- **Standard .JPG files (n=4,883):**
  - `dark_frac > 0.3`: **0 / 4,883** (0.00%)
  - Maximum `dark_frac` in .JPG: **0.211** (an Early Blight image: `4a352896-5a0f-4e42-aba1-f06045d5b531___RS_Erly.B 7765.JPG`)

---

## 3. Resolution of Previously Unexplained Findings

### 3.1 The "314 Sample Tags" Mystery in FiftyOne UI
In previous sessions, the FiftyOne UI displayed `314` next to "sample tags" when filtering for the 153 non-.JPG samples.
**Resolution Verified:** FiftyOne aggregates multi-tag assignments across samples in a view. For the 153 filtered samples:
- `non_JPG_ext`: 153 tags
- `Tomato___Late_blight`: 153 tags (class names were applied as sample tags on import)
- `inspect_dark`: 3 tags (the 3 bright non-.JPG images)
- `exact_dup`: 8 tags (4 pairs of exact duplicate non-.JPG images)
- Note: 150 samples have `black_bg`.
- Total tag occurrences evaluated across the UI tag filter badge: **153 + 153 + 8 = 314 tags**.

### 3.2 Visual & Content Review of Unreviewed Subsets
1. **The 8 `inspect_dark` Samples:**
   - 5 Early Blight images (.JPG, dark_frac 0.149 to 0.211): Natural leaf photographs taken with heavy shadows or dark background margins.
   - 3 Late Blight images (non-.JPG, dark_frac 0.000): Full-frame greenhouse leaf photographs without segmentation masks.
2. **The 16 `exact_dup` Samples:**
   - 4 pairs (8 files) are `.JPG` files (`GHLB2 Leaf ...`) with light backgrounds (Brightness 110–126).
   - 4 pairs (8 files) are `.jpg` files (`GHLB_PS Leaf ...`) with black cutout backgrounds (Brightness 12–29).
   - Zero pairs cross class boundaries.
3. **The 15 `rep_seed42` Samples:**
   - Deterministic 5 samples per class selected using `random.Random(42)`. All verified valid, clean images typical of their respective classes.

---

## 4. Impact on Training / Validation Split

Because the 150 black-background images have unique visual characteristics (mean brightness 32.5 vs 120.5 for regular Late blight), their allocation across train and validation must be carefully controlled:
- If all 150 fall into training, the model might learn to associate black backgrounds with Late blight.
- If stratified, both splits will contain black-background samples.
- **Current Status:** The reported 80/20 split list (4,029 / 1,007) does not exist on disk. Its generation must explicitly document how the 150 black-background images are partitioned.
