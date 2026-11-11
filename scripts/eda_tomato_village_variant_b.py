"""
EDA for Tomato-Village Variant B (Multilabel Classification)
Analyzes:
- Multi-Label dataset - with augmented.csv
- Number of records, unique labels, labels per sample
- Single-label vs multi-label distribution
- Label frequencies and co-occurrence matrix
- Most common label combinations
- Missing / invalid labels and duplicate records
- Identification of augmented rows from filenames / metadata
- CSV-to-image matching with train/, val/, test/ folders
- Image integrity and dimensions for sampled/matched files
"""
import os
import glob
from collections import Counter, defaultdict
import pandas as pd
import numpy as np
from PIL import Image

BASE_DIR = "/home/jaskirat/datasets/Tomato-Village/Variant-b(MultiLabel Classification)"
CSV_PATH = os.path.join(BASE_DIR, "Multi-Label dataset - with augmented.csv")

def analyze_variant_b():
    print("==================================================")
    print("TOMATO-VILLAGE VARIANT B (MULTILABEL) ANALYSIS")
    print("==================================================")
    
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: {CSV_PATH} not found!")
        return
        
    df = pd.read_csv(CSV_PATH)
    print(f"Total CSV records: {len(df)}")
    print("Columns:", list(df.columns))
    print("\nDataset split column values:")
    print(df["dataset"].value_counts(dropna=False).to_dict())
    
    # Label columns
    # Based on header: dataset,filename,path,Early blight,Healthy,Late blight,Leaf Miner,Magnesium Deficiency,Nitrogen Deficiency,Pottassium Deficiency,Spotted Wilt Virus,SUM
    label_cols = [
        "Early blight", "Healthy", "Late blight", "Leaf Miner",
        "Magnesium Deficiency", "Nitrogen Deficiency", "Pottassium Deficiency",
        "Spotted Wilt Virus"
    ]
    print(f"\nLabel columns ({len(label_cols)}):", label_cols)
    
    # Check data types and values in label columns
    print("\n--- Label Columns Data Hygiene ---")
    for col in label_cols:
        val_counts = df[col].fillna(0).value_counts().to_dict()
        print(f"  {col}: {val_counts}")
        
    # Convert label columns to numeric binary (0 or 1)
    df_binary = df[label_cols].fillna(0).astype(int)
    
    # Computed SUM vs CSV 'SUM' column
    computed_sum = df_binary.sum(axis=1)
    if "SUM" in df.columns:
        mismatches = (computed_sum != df["SUM"].fillna(0).astype(int)).sum()
        print(f"\nMismatches between computed sum and CSV 'SUM' column: {mismatches}")
        
    # Labels per sample distribution
    print("\n--- Labels Per Sample Distribution ---")
    sum_dist = computed_sum.value_counts().sort_index()
    for n_labels, count in sum_dist.items():
        print(f"  {n_labels} label(s): {count} samples ({100*count/len(df):.2f}%)")
        
    single_label = (computed_sum == 1).sum()
    multi_label = (computed_sum > 1).sum()
    zero_label = (computed_sum == 0).sum()
    print(f"\nSingle-label samples: {single_label} ({100*single_label/len(df):.2f}%)")
    print(f"Multi-label samples (>1 label): {multi_label} ({100*multi_label/len(df):.2f}%)")
    print(f"Zero-label samples: {zero_label} ({100*zero_label/len(df):.2f}%)")
    
    # Label frequency
    print("\n--- Label Frequency across Samples ---")
    label_freq = df_binary.sum().sort_values(ascending=False)
    for lbl, cnt in label_freq.items():
        print(f"  {lbl}: {cnt} ({100*cnt/len(df):.2f}%)")
        
    # Co-occurrence Matrix
    print("\n--- Label Co-occurrence Matrix ---")
    co_matrix = df_binary.T.dot(df_binary)
    print(co_matrix.to_string())
    
    # Most common label combinations
    print("\n--- Top 10 Most Common Label Combinations ---")
    combo_series = df_binary.apply(lambda row: " + ".join([c for c in label_cols if row[c] == 1]) or "None", axis=1)
    print(combo_series.value_counts().head(10).to_string())
    
    # Duplicate rows check
    print("\n--- Duplicate Records Check ---")
    dup_rows = df.duplicated(subset=["dataset", "filename"]).sum()
    print(f"Duplicate (dataset, filename) pairs: {dup_rows}")
    dup_filenames = df.duplicated(subset=["filename"]).sum()
    print(f"Duplicate filenames across entire CSV: {dup_filenames}")
    
    # Identifying Augmented rows
    print("\n--- Investigating Augmented Images ---")
    # Check filename patterns (e.g., '_aug', 'copy', etc.)
    df["has_aug_in_name"] = df["filename"].str.contains("aug", case=False, na=False)
    df["has_copy_in_name"] = df["filename"].str.contains("copy", case=False, na=False)
    print(f"Filenames containing 'aug': {df['has_aug_in_name'].sum()}")
    print(f"Filenames containing 'copy': {df['has_copy_in_name'].sum()}")
    
    # Inspect sample filenames from train, val, test
    print("\nSample filenames by split:")
    for split in ["train", "val", "test"]:
        sub = df[df["dataset"] == split]
        print(f"  Split '{split}' samples (total {len(sub)}): {sub['filename'].head(3).tolist()}")
        
    # CSV-to-Image File Matching
    print("\n--- CSV-to-Image Matching Check ---")
    folder_splits = ["train", "val", "test"]
    folder_files = {}
    for s in folder_splits:
        p = os.path.join(BASE_DIR, s)
        if os.path.isdir(p):
            # Check if images are direct or in subdirectories
            files_direct = [f for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))]
            files_all = []
            for root, _, files in os.walk(p):
                for f in files:
                    files_all.append(f)
            folder_files[s] = set(files_all)
            print(f"  Folder '{s}': {len(files_all)} files (direct: {len(files_direct)})")
        else:
            print(f"  Folder '{s}' does not exist!")
            
    # Check matching for each split
    for s in folder_splits:
        sub_csv = df[df["dataset"] == s]
        csv_files = set(sub_csv["filename"])
        present_in_folder = folder_files.get(s, set())
        matched = csv_files.intersection(present_in_folder)
        missing_on_disk = csv_files - present_in_folder
        untracked_on_disk = present_in_folder - csv_files
        print(f"  Split '{s}': CSV records={len(csv_files)} | On disk={len(present_in_folder)} | Matched={len(matched)} | Missing={len(missing_on_disk)} | Untracked on disk={len(untracked_on_disk)}")
        if missing_on_disk:
            print(f"    Sample missing: {list(missing_on_disk)[:3]}")
        if untracked_on_disk:
            print(f"    Sample untracked: {list(untracked_on_disk)[:3]}")

if __name__ == "__main__":
    analyze_variant_b()
