# PlantDoc EDA — Verification, Near-Duplicate Leakage & Comparison Report

**Dataset:** PlantDoc Dataset  
**Source Path:** `/home/jaskirat/PlantDoc-Dataset`  
**Paper Reference:** Singh et al., "PlantDoc: A Dataset for Visual Plant Disease Detection" (CoDS-COMAD 2020).  
**Original Scope:** 2,578 accessible image files across 13 plant species, 27–28 disease classes.  
**AgriMind Target Subset:** 3 tomato classes (`Tomato leaf bacterial spot`, `Tomato Early blight leaf`, `Tomato leaf late blight`).  
**Verification Script:** `scripts/eda_plantdoc.py`.

---

## 1. Tomato 3-Class Inventory & Split Verification

Every file in the three tomato classes was inspected, verified with Pillow, decoded, and inventoried:

| AgriMind Class Label | Native Folder Name | Train Count | Test Count | Total Count | Class % |
|---|---|---|---|---|---|
| **Bacterial_spot** | `Tomato leaf bacterial spot` | **101** | **9** | **110** | 35.60% |
| **Early_blight** | `Tomato Early blight leaf` | **79** | **9** | **88** | 28.48% |
| **Late_blight** | `Tomato leaf late blight` | **101** | **10** | **111** | 35.92% |
| **Total** | — | **281** | **28** | **309** | 100.00% |

- **Reported Counts Confirmed:** The reported counts (Train: **101 / 79 / 101 = 281**; Test: **9 / 9 / 10 = 28**) match the filesystem 100%.

---

## 2. Image Properties & Technical Specifications

- **Image Readability & Integrity:** **0 failures** out of 309 images.
- **Image Format:** 100% **JPEG**, color mode **RGB** (3 channels).
- **Image Dimensions:** High variability:
  - Width: min **150 px**, max **4,416 px**, mean **917.1 px**
  - Height: min **150 px**, max **3,370 px**, mean **761.0 px**
  - **Distinct Resolution Pairs:** **226 different resolutions** across 309 images (contrast with PlantVillage where 100% are 256x256).
- **Exact Duplicates (MD5):** **0 exact duplicates** (309 unique MD5 hashes).

---

## 3. Near-Duplicate Analysis & Verified Cross-Split Leakage

Using Difference Hash (`dHash`, 8x8 gradient comparison, 64 bits) with Hamming distance threshold $\le 4$:

### 3.1 Verification of Specifically Reported Leakage Pairs
Both specifically reported near-duplicate cross-split pairs were verified with dHash distance = 0 (identical visual content, different resolutions/crops):

1. **Pair 1 (Bacterial Spot Train-to-Test Leakage):**
   - **Train Image:** `bacterial-canker3x2400-2ia1kgd.jpg` (Resolution: high-res 2400 px)
   - **Test Image:** `07.17.18-Common_Tomato_Diseases_Canker-258x300.jpg` (Resolution: 258x300 thumbnail)
   - **Measured dHash Distance:** **0** (Exact visual match; Direct Data Leakage!).
2. **Pair 2 (Late Blight Train-to-Test Leakage):**
   - **Train Image:** `late_blight1.jpg`
   - **Test Image:** `18c.jpg`
   - **Measured dHash Distance:** **0** (Exact visual match; Direct Data Leakage!).

### 3.2 Additional Near-Duplicates Identified
- **Within Train Set Duplicates (dHash = 0):**
  - Bacterial Spot: `BCH%20medium%20thumbnail%20for%20upload%20%2814%29.jpg` $\leftrightarrow$ `BCH%20small%20thumbnail%20for%20upload%20%2814%29.jpg`
  - Early Blight: `EBTomato.jpg` $\leftrightarrow$ `tomatoblight.jpg`
  - Early Blight: `Early-bligh_t.jpg` $\leftrightarrow$ `Early-blight.jpg`
  - Late Blight: `20150619d.jpg` $\leftrightarrow$ `IMG_5360.jpg`
  - Late Blight: `924977LateBlightLeaf.jpg` $\leftrightarrow$ `LateBlightLeaf.jpg`
  - Late Blight: `TomatoLateBlight-3-Underside-2ebj05b-300x225.jpg` $\leftrightarrow$ `symptoms_of_late_blight.jpg2__0.jpg`
- **Cross-Label Near-Duplicate (Potential Annotation Noise):**
  - `p1020084s.jpg` (labeled Early Blight) $\leftrightarrow$ `tomato_late-blight_04_zoom.jpg` (labeled Late Blight) has **dHash distance 1**, indicating near-identical visual features assigned conflicting labels.

### 3.3 Training Pool Impact
Excluding the two leaked training images (`bacterial-canker3x2400-2ia1kgd.jpg` and `late_blight1.jpg`) reduces the training pool from **281 to 279**:
- Bacterial spot: $101 - 1 = 100$
- Early blight: $79 - 0 = 79$
- Late blight: $101 - 1 = 100$
- Proposed 80/20 internal split of 279: **80 / 63 / 80 (223 train)** and **20 / 16 / 20 (56 val)**.

---

## 4. Measured Quantitative Comparison: PlantVillage vs PlantDoc

| Property | PlantVillage (Tomato 3-Class) | PlantDoc (Tomato 3-Class) | Quantitative Difference |
|---|---|---|---|
| **Sample Size** | 5,036 | 309 | PlantVillage is 16.3x larger |
| **Image Resolution** | Uniform 256x256 (1 distinct size) | 150x150 to 4416x3370 (226 distinct sizes) | PlantDoc has high geometric variance |
| **Aspect Ratio** | Fixed 1.0 (Square) | Variable (0.42 to 2.35) | PlantDoc has diverse framing |
| **Mean Brightness** | 104.9 to 113.4 | 113.2 to 123.1 | PlantDoc images are slightly brighter |
| **Mean Contrast (Std)** | 33.4 to 46.3 | 49.4 to 50.9 | PlantDoc has higher average contrast |
| **Dark Background (`dark_frac > 0.3`)** | 150 images (3.0% overall, 7.9% of Late blight) | 5 images (1.6% overall) | PlantVillage has artificial black cutouts |
| **Exact Duplicates** | 16 images (8 pairs of 2) | 0 images | PlantVillage contains duplicate files |
| **Train/Test Leakage** | Needs split list definition | 2 verified pairs with dHash = 0 | PlantDoc official test set has leakage |
