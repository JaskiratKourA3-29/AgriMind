"""
Generate train_split.csv and val_split.csv for PlantVillage 3-class Tomato subset.
Strict requirements:
- Deterministic with seed 42
- Stratified 80/20 per class (Bacterial: 1702/425, Early: 800/200, Late: 1527/382; Total: 4029/1007)
- Group exact-duplicates atomically so no duplicate pair is split across train and val
- Distribute the 150 black-background images proportionally (120 in train / 30 in val)
- Check that output paths do NOT already exist before writing (refuse overwrite)
- Verify read-back from disk
"""
import os
import hashlib
import pandas as pd
import numpy as np

OUTPUTS_DIR = os.path.expanduser("~/agrimind-fiftyone-eda/outputs")
WORKSPACE_DIR = "/mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project"
SPLITS_DIR = os.path.join(WORKSPACE_DIR, "data_splits")
TRAIN_SPLIT_PATH = os.path.join(SPLITS_DIR, "train_split.csv")
VAL_SPLIT_PATH = os.path.join(SPLITS_DIR, "val_split.csv")

def main():
    print("=== PLANTVILLAGE DATA PREPARATION & SPLIT GENERATION ===")
    
    # 1. Output path existence check
    print(f"Target split directory: {SPLITS_DIR}")
    print(f"Target train split path: {TRAIN_SPLIT_PATH}")
    print(f"Target val split path: {VAL_SPLIT_PATH}")
    
    if os.path.exists(TRAIN_SPLIT_PATH):
        raise FileExistsError(f"Train split file already exists at {TRAIN_SPLIT_PATH}; refusing to overwrite.")
    if os.path.exists(VAL_SPLIT_PATH):
        raise FileExistsError(f"Val split file already exists at {VAL_SPLIT_PATH}; refusing to overwrite.")
        
    os.makedirs(SPLITS_DIR, exist_ok=True)
    
    # 2. Load verified artifacts
    stats_csv = os.path.join(OUTPUTS_DIR, "plantvillage_image_stats.csv")
    dark_csv = os.path.join(OUTPUTS_DIR, "plantvillage_dark_frac.csv")
    dup_csv = os.path.join(OUTPUTS_DIR, "plantvillage_md5_duplicates.csv")
    
    df_stats = pd.read_csv(stats_csv)
    df_dark = pd.read_csv(dark_csv)
    df_dup = pd.read_csv(dup_csv)
    
    df = df_stats.merge(df_dark[["filepath", "dark_frac"]], on="filepath")
    df = df.sort_values("filepath").reset_index(drop=True)
    
    # Compute MD5
    md5_dict = {}
    for p in df["filepath"]:
        with open(p, "rb") as f:
            md5_dict[p] = hashlib.md5(f.read()).hexdigest()
    df["md5"] = df["filepath"].map(md5_dict)
    
    dup_md5s = set(df_dup["md5"])
    df["is_exact_dup"] = df["md5"].isin(dup_md5s)
    df["is_black_bg"] = df["dark_frac"] > 0.3
    
    # Random state
    rng = np.random.RandomState(42)
    
    train_indices = []
    val_indices = []
    
    # A. Bacterial Spot (2,127 samples, all unique, 0 black_bg)
    bs_df = df[df["label"] == "Tomato___Bacterial_spot"]
    bs_idx = bs_df.index.to_numpy().copy()
    rng.shuffle(bs_idx)
    val_bs = bs_idx[:425]
    train_bs = bs_idx[425:]
    assert len(train_bs) == 1702 and len(val_bs) == 425
    train_indices.extend(train_bs)
    val_indices.extend(val_bs)
    
    # B. Early Blight (1,000 samples, all unique, 0 black_bg)
    eb_df = df[df["label"] == "Tomato___Early_blight"]
    eb_idx = eb_df.index.to_numpy().copy()
    rng.shuffle(eb_idx)
    val_eb = eb_idx[:200]
    train_eb = eb_idx[200:]
    assert len(train_eb) == 800 and len(val_eb) == 200
    train_indices.extend(train_eb)
    val_indices.extend(val_eb)
    
    # C. Late Blight (1,909 samples)
    lb_df = df[df["label"] == "Tomato___Late_blight"]
    
    # Subgroup C1: Late Blight Black-Background (150 samples)
    lb_bb = lb_df[lb_df["is_black_bg"]]
    bb_dup_groups = [lb_bb[lb_bb["md5"] == h].index.tolist() for h in sorted(lb_bb["md5"].unique()) if len(lb_bb[lb_bb["md5"] == h]) > 1]
    bb_singles = lb_bb[~lb_bb["is_exact_dup"]].index.tolist()
    assert len(bb_dup_groups) == 4
    assert len(bb_singles) == 142
    
    perm_bb_dups = rng.permutation(len(bb_dup_groups))
    val_bb_dups = [idx for i in perm_bb_dups[:1] for idx in bb_dup_groups[i]]
    train_bb_dups = [idx for i in perm_bb_dups[1:] for idx in bb_dup_groups[i]]
    
    perm_bb_singles = rng.permutation(bb_singles)
    val_bb_singles = perm_bb_singles[:28].tolist()
    train_bb_singles = perm_bb_singles[28:].tolist()
    
    val_lb_bb = val_bb_dups + val_bb_singles
    train_lb_bb = train_bb_dups + train_bb_singles
    assert len(val_lb_bb) == 30 and len(train_lb_bb) == 120
    
    # Subgroup C2: Late Blight Normal Light Background (1,759 samples)
    lb_norm = lb_df[~lb_df["is_black_bg"]]
    norm_dup_groups = [lb_norm[lb_norm["md5"] == h].index.tolist() for h in sorted(lb_norm["md5"].unique()) if len(lb_norm[lb_norm["md5"] == h]) > 1]
    norm_singles = lb_norm[~lb_norm["is_exact_dup"]].index.tolist()
    assert len(norm_dup_groups) == 4
    assert len(norm_singles) == 1751
    
    perm_norm_dups = rng.permutation(len(norm_dup_groups))
    val_norm_dups = [idx for i in perm_norm_dups[:1] for idx in norm_dup_groups[i]]
    train_norm_dups = [idx for i in perm_norm_dups[1:] for idx in norm_dup_groups[i]]
    
    perm_norm_singles = rng.permutation(norm_singles)
    val_norm_singles = perm_norm_singles[:350].tolist()
    train_norm_singles = perm_norm_singles[350:].tolist()
    
    val_lb_norm = val_norm_dups + val_norm_singles
    train_lb_norm = train_norm_dups + train_norm_singles
    assert len(val_lb_norm) == 352 and len(train_lb_norm) == 1407
    
    train_lb = train_lb_bb + train_lb_norm
    val_lb = val_lb_bb + val_lb_norm
    assert len(train_lb) == 1527 and len(val_lb) == 382
    
    train_indices.extend(train_lb)
    val_indices.extend(val_lb)
    
    # 3. Assemble and sort DataFrames
    cols_to_save = ["label", "filepath", "md5", "is_black_bg", "dark_frac", "brightness", "contrast"]
    df_train = df.loc[train_indices, cols_to_save].sort_values("filepath").reset_index(drop=True)
    df_val = df.loc[val_indices, cols_to_save].sort_values("filepath").reset_index(drop=True)
    df_train["split"] = "train"
    df_val["split"] = "val"
    
    # Add filename column for convenience
    df_train["filename"] = df_train["filepath"].apply(os.path.basename)
    df_val["filename"] = df_val["filepath"].apply(os.path.basename)
    
    # 4. Save CSV files
    df_train.to_csv(TRAIN_SPLIT_PATH, index=False)
    df_val.to_csv(VAL_SPLIT_PATH, index=False)
    print(f"\nSuccessfully wrote {TRAIN_SPLIT_PATH} ({len(df_train)} rows)")
    print(f"Successfully wrote {VAL_SPLIT_PATH} ({len(df_val)} rows)")
    
    # 5. Read back and perform rigorous verification
    print("\n=== POST-WRITE AUDIT & VERIFICATION ===")
    read_train = pd.read_csv(TRAIN_SPLIT_PATH)
    read_val = pd.read_csv(VAL_SPLIT_PATH)
    
    print(f"Verified Train row count: {len(read_train)}")
    print(f"Verified Val row count: {len(read_val)}")
    assert len(read_train) == 4029, f"Train count mismatch: {len(read_train)}"
    assert len(read_val) == 1007, f"Val count mismatch: {len(read_val)}"
    
    # Per-class counts
    train_counts = read_train["label"].value_counts().to_dict()
    val_counts = read_val["label"].value_counts().to_dict()
    print("Verified Train class counts:", train_counts)
    print("Verified Val class counts:", val_counts)
    assert train_counts == {'Tomato___Bacterial_spot': 1702, 'Tomato___Late_blight': 1527, 'Tomato___Early_blight': 800}
    assert val_counts == {'Tomato___Bacterial_spot': 425, 'Tomato___Late_blight': 382, 'Tomato___Early_blight': 200}
    
    # Overlap check
    train_set = set(read_train["filepath"])
    val_set = set(read_val["filepath"])
    file_overlap = train_set.intersection(val_set)
    print(f"Verified Filepath overlap: {len(file_overlap)}")
    assert len(file_overlap) == 0, f"File overlap detected: {file_overlap}"
    
    # Duplicate group separation
    train_md5_set = set(read_train["md5"])
    val_md5_set = set(read_val["md5"])
    dup_leaks = train_md5_set.intersection(val_md5_set).intersection(dup_md5s)
    print(f"Verified Duplicate MD5 leaks: {len(dup_leaks)}")
    assert len(dup_leaks) == 0, f"Duplicate leakage detected: {dup_leaks}"
    
    # Duplicate group distribution
    train_dups = read_train[read_train["md5"].isin(dup_md5s)]
    val_dups = read_val[read_val["md5"].isin(dup_md5s)]
    print(f"Train duplicate files: {len(train_dups)} (in {train_dups['md5'].nunique()} groups)")
    print(f"Val duplicate files: {len(val_dups)} (in {val_dups['md5'].nunique()} groups)")
    assert len(train_dups) == 12 and train_dups["md5"].nunique() == 6
    assert len(val_dups) == 4 and val_dups["md5"].nunique() == 2
    
    # Black-background distribution
    train_bb = read_train["is_black_bg"].sum()
    val_bb = read_val["is_black_bg"].sum()
    print(f"Verified Train black_bg: {train_bb} ({100*train_bb/len(read_train):.2f}% of train, {100*train_bb/150:.2f}% of total black_bg)")
    print(f"Verified Val black_bg: {val_bb} ({100*val_bb/len(read_val):.2f}% of val, {100*val_bb/150:.2f}% of total black_bg)")
    assert train_bb == 120 and val_bb == 30, f"Black bg mismatch: train={train_bb}, val={val_bb}"
    
    print("\nALL VERIFICATIONS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
