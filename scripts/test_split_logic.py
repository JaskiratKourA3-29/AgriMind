"""
Simulation of clean, group-aware, stratified 80/20 split with seed 42:
- Exactly 1702/425 Bacterial spot
- Exactly 800/200 Early blight
- Exactly 1527/382 Late blight
- Exactly 120/30 black-background distribution (80/20)
- Zero duplicate pair leakage (atomic duplicate units)
- Deterministic with seed 42
"""
import os
import hashlib
import pandas as pd
import numpy as np

OUTPUTS_DIR = os.path.expanduser("~/agrimind-fiftyone-eda/outputs")

def generate_partition():
    stats_csv = os.path.join(OUTPUTS_DIR, "plantvillage_image_stats.csv")
    dark_csv = os.path.join(OUTPUTS_DIR, "plantvillage_dark_frac.csv")
    dup_csv = os.path.join(OUTPUTS_DIR, "plantvillage_md5_duplicates.csv")
    
    df_stats = pd.read_csv(stats_csv)
    df_dark = pd.read_csv(dark_csv)
    df_dup = pd.read_csv(dup_csv)
    
    df = df_stats.merge(df_dark[["filepath", "dark_frac"]], on="filepath")
    df = df.sort_values("filepath").reset_index(drop=True)
    
    # Compute MD5 mapping
    md5_dict = {}
    for p in df["filepath"]:
        with open(p, "rb") as f:
            md5_dict[p] = hashlib.md5(f.read()).hexdigest()
    df["md5"] = df["filepath"].map(md5_dict)
    
    dup_md5s = set(df_dup["md5"])
    df["is_exact_dup"] = df["md5"].isin(dup_md5s)
    df["is_black_bg"] = df["dark_frac"] > 0.3
    
    rng = np.random.RandomState(42)
    
    train_indices = []
    val_indices = []
    
    # 1. Bacterial Spot (2,127 samples, all unique, 0 black_bg)
    bs_df = df[df["label"] == "Tomato___Bacterial_spot"]
    bs_idx = bs_df.index.to_numpy().copy()
    rng.shuffle(bs_idx)
    val_bs = bs_idx[:425]
    train_bs = bs_idx[425:]
    assert len(train_bs) == 1702 and len(val_bs) == 425
    train_indices.extend(train_bs)
    val_indices.extend(val_bs)
    
    # 2. Early Blight (1,000 samples, all unique, 0 black_bg)
    eb_df = df[df["label"] == "Tomato___Early_blight"]
    eb_idx = eb_df.index.to_numpy().copy()
    rng.shuffle(eb_idx)
    val_eb = eb_idx[:200]
    train_eb = eb_idx[200:]
    assert len(train_eb) == 800 and len(val_eb) == 200
    train_indices.extend(train_eb)
    val_indices.extend(val_eb)
    
    # 3. Late Blight (1,909 samples)
    # Target: 1527 train, 382 val
    # Black-bg target: 120 train, 30 val (out of 150)
    # Normal Late blight target: 1407 train, 352 val (out of 1,759)
    lb_df = df[df["label"] == "Tomato___Late_blight"]
    
    # Subgroup 3a: Late Blight Black-Background (150 samples)
    lb_bb = lb_df[lb_df["is_black_bg"]]
    bb_dup_groups = [lb_bb[lb_bb["md5"] == h].index.tolist() for h in sorted(lb_bb["md5"].unique()) if len(lb_bb[lb_bb["md5"] == h]) > 1]
    bb_singles = lb_bb[~lb_bb["is_exact_dup"]].index.tolist()
    assert len(bb_dup_groups) == 4  # 4 pairs = 8 samples
    assert len(bb_singles) == 142   # 142 singles
    
    # Allocate 1 dup group (2 samples) + 28 singles to val = 30 samples
    # Allocate 3 dup groups (6 samples) + 114 singles to train = 120 samples
    perm_bb_dups = rng.permutation(len(bb_dup_groups))
    val_bb_dups = [idx for i in perm_bb_dups[:1] for idx in bb_dup_groups[i]]
    train_bb_dups = [idx for i in perm_bb_dups[1:] for idx in bb_dup_groups[i]]
    
    perm_bb_singles = rng.permutation(bb_singles)
    val_bb_singles = perm_bb_singles[:28].tolist()
    train_bb_singles = perm_bb_singles[28:].tolist()
    
    val_lb_bb = val_bb_dups + val_bb_singles
    train_lb_bb = train_bb_dups + train_bb_singles
    assert len(val_lb_bb) == 30 and len(train_lb_bb) == 120
    
    # Subgroup 3b: Late Blight Normal JPG (1,759 samples)
    lb_norm = lb_df[~lb_df["is_black_bg"]]
    norm_dup_groups = [lb_norm[lb_norm["md5"] == h].index.tolist() for h in sorted(lb_norm["md5"].unique()) if len(lb_norm[lb_norm["md5"] == h]) > 1]
    norm_singles = lb_norm[~lb_norm["is_exact_dup"]].index.tolist()
    assert len(norm_dup_groups) == 4  # 4 pairs = 8 samples
    assert len(norm_singles) == 1751  # 1751 singles
    
    # Allocate 1 dup group (2 samples) + 350 singles to val = 352 samples
    # Allocate 3 dup groups (6 samples) + 1401 singles to train = 1407 samples
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
    
    df_train = df.loc[train_indices].sort_values("filepath").reset_index(drop=True)
    df_val = df.loc[val_indices].sort_values("filepath").reset_index(drop=True)
    
    print("=== PARTITION VALIDATION ===")
    print(f"Train total: {len(df_train)} (Expected: 4029)")
    print(f"Val total: {len(df_val)} (Expected: 1007)")
    print("Train class counts:", df_train["label"].value_counts().to_dict())
    print("Val class counts:", df_val["label"].value_counts().to_dict())
    
    # Overlap check on filepaths
    train_files = set(df_train["filepath"])
    val_files = set(df_val["filepath"])
    overlap_files = train_files.intersection(val_files)
    print(f"Filepath overlap: {len(overlap_files)}")
    
    # Duplicate group leakage check
    train_md5s = set(df_train["md5"])
    val_md5s = set(df_val["md5"])
    overlap_md5s = train_md5s.intersection(val_md5s)
    dup_leaks = overlap_md5s.intersection(dup_md5s)
    print(f"Duplicate MD5 leaks between train and val: {len(dup_leaks)}")
    
    # Black-background distribution
    bb_train = df_train["is_black_bg"].sum()
    bb_val = df_val["is_black_bg"].sum()
    print(f"Train black_bg count: {bb_train} ({100*bb_train/len(df_train):.2f}% of train, {100*bb_train/150:.2f}% of total black_bg)")
    print(f"Val black_bg count: {bb_val} ({100*bb_val/len(df_val):.2f}% of val, {100*bb_val/150:.2f}% of total black_bg)")

if __name__ == "__main__":
    generate_partition()
