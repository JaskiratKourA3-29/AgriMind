"""
EDA for Tomato-Village Variant A (Multiclass Classification)
Computes:
- Class counts and percentages across train, val, test, total
- Image integrity, formats, dimensions, channels
- Exact MD5 duplicates within and across classes and splits
- Brightness, contrast, dark_frac (gray < 15)
- File sizes
- Predefined splits and leakage check
"""
import os
import glob
import hashlib
from collections import Counter, defaultdict
from PIL import Image
import numpy as np
import pandas as pd

BASE_DIR = "/home/jaskirat/datasets/Tomato-Village/Variant-a(Multiclass Classification)"

def analyze_variant_a():
    print("==================================================")
    print("TOMATO-VILLAGE VARIANT A (MULTICLASS) ANALYSIS")
    print("==================================================")
    
    splits = ["train", "val", "test"]
    split_counts = defaultdict(Counter)
    all_files = []
    
    for split in splits:
        split_path = os.path.join(BASE_DIR, split)
        if not os.path.isdir(split_path):
            print(f"Directory missing: {split_path}")
            continue
        for class_name in sorted(os.listdir(split_path)):
            class_dir = os.path.join(split_path, class_name)
            if not os.path.isdir(class_dir):
                continue
            files = [f for f in os.listdir(class_dir) if os.path.isfile(os.path.join(class_dir, f))]
            split_counts[split][class_name] = len(files)
            for f in files:
                all_files.append({
                    "split": split,
                    "class": class_name,
                    "filename": f,
                    "filepath": os.path.join(class_dir, f)
                })

    df_meta = pd.DataFrame(all_files)
    print(f"\nTotal images found across all splits: {len(df_meta)}")
    
    # Summary table per split and class
    df_counts = pd.DataFrame(split_counts).fillna(0).astype(int)
    df_counts["Total"] = df_counts.sum(axis=1)
    df_counts["% Total"] = (100 * df_counts["Total"] / len(df_meta)).round(2)
    print("\n--- Class Distribution across Predefined Splits ---")
    print(df_counts.to_string())
    print("\nTotal by Split:")
    print(df_counts[["train", "val", "test", "Total"]].sum().to_string())
    
    # Image integrity, dimensions, channels, formats, file sizes, MD5
    print("\n--- Inspecting Image Files (Integrity, Dimensions, Formats, Stats) ---")
    bad_files = []
    formats = Counter()
    dimensions = Counter()
    channels = Counter()
    file_sizes = []
    md5_to_files = defaultdict(list)
    stats_records = []
    
    for idx, row in df_meta.iterrows():
        p = row["filepath"]
        size_bytes = os.path.getsize(p)
        file_sizes.append(size_bytes)
        
        # MD5
        try:
            with open(p, "rb") as f:
                h = hashlib.md5(f.read()).hexdigest()
            md5_to_files[h].append((row["split"], row["class"], row["filename"]))
        except Exception as e:
            bad_files.append((p, f"MD5 read failed: {e}"))
            continue
            
        # Pillow verify + decode
        try:
            with Image.open(p) as img:
                img.verify()
            with Image.open(p) as img:
                formats[img.format] += 1
                dimensions[img.size] += 1
                channels[img.mode] += 1
                rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
                gray = np.asarray(img.convert("L"), dtype=np.float32)
                
            b = float(gray.mean())
            c = float(gray.std())
            dark = float((gray < 15).mean())
            stats_records.append({
                "split": row["split"],
                "class": row["class"],
                "brightness": b,
                "contrast": c,
                "dark_frac": dark,
                "size_bytes": size_bytes
            })
        except Exception as e:
            bad_files.append((p, f"Pillow failed: {e}"))
            
    print(f"Integrity check failures: {len(bad_files)}")
    if bad_files:
        print("Failures:", bad_files[:5])
    print(f"Image Formats: {dict(formats)}")
    print(f"Image Channels/Modes: {dict(channels)}")
    print(f"Distinct Dimensions count: {len(dimensions)}")
    print(f"Top 5 Dimensions: {dimensions.most_common(5)}")
    print(f"File sizes (bytes) - Min: {min(file_sizes)}, Max: {max(file_sizes)}, Mean: {np.mean(file_sizes):.1f}")
    
    # Exact Duplicates (MD5)
    dup_groups = {h: flist for h, flist in md5_to_files.items() if len(flist) > 1}
    print(f"\n--- Exact Duplicates (MD5) ---")
    print(f"Unique MD5 hashes: {len(md5_to_files)}")
    print(f"Duplicate MD5 groups: {len(dup_groups)}")
    total_dup_files = sum(len(flist) for flist in dup_groups.values())
    print(f"Total duplicate file instances: {total_dup_files}")
    
    cross_split_dups = []
    cross_class_dups = []
    within_class_dups = []
    
    for h, flist in dup_groups.items():
        splits_in_group = set(x[0] for x in flist)
        classes_in_group = set(x[1] for x in flist)
        if len(splits_in_group) > 1:
            cross_split_dups.append((h, flist))
        if len(classes_in_group) > 1:
            cross_class_dups.append((h, flist))
        else:
            within_class_dups.append((h, flist))
            
    print(f"Duplicate groups spanning >1 split (LEAKAGE): {len(cross_split_dups)}")
    print(f"Duplicate groups spanning >1 class (LABEL INCONSISTENCY): {len(cross_class_dups)}")
    print(f"Duplicate groups purely within the same class and split: {len(within_class_dups) - len(cross_split_dups)}")
    if cross_split_dups:
        print("Sample cross-split duplicate:", cross_split_dups[0])
    if cross_class_dups:
        print("Sample cross-class duplicate:", cross_class_dups[0])
        
    # Brightness, contrast, dark_frac per class
    df_stats = pd.DataFrame(stats_records)
    print("\n--- Brightness, Contrast & dark_frac per Class ---")
    agg_class = df_stats.groupby("class").agg(
        n=("brightness", "size"),
        brightness_mean=("brightness", "mean"),
        brightness_std=("brightness", "std"),
        contrast_mean=("contrast", "mean"),
        contrast_std=("contrast", "std"),
        dark_frac_mean=("dark_frac", "mean"),
        dark_frac_max=("dark_frac", "max")
    ).round(2)
    print(agg_class.to_string())
    
    print("\n--- dark_frac Distribution (Thresholds 0.1, 0.3, 0.5) ---")
    for t in [0.1, 0.3, 0.5]:
        count = (df_stats["dark_frac"] > t).sum()
        print(f"Images with dark_frac > {t}: {count} ({100*count/len(df_stats):.2f}%)")

if __name__ == "__main__":
    analyze_variant_a()
