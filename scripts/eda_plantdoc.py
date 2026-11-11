"""
EDA for PlantDoc Dataset
Analyzes:
- Overall dataset inventory and class counts in train and test
- AgriMind 3 tomato classes subset:
  - Tomato leaf bacterial spot
  - Tomato Early blight leaf
  - Tomato leaf late blight
- Verification of train (101/79/101 = 281) and test (9/9/10 = 28)
- Image readability, formats, dimensions, channels, file sizes
- Exact duplicates (MD5)
- Near duplicates (dHash calculation and distance threshold)
- Brightness (mean gray), Contrast (std gray), dark_frac (gray < 15)
- Quantitative comparison with PlantVillage measurements
"""
import os
import glob
import hashlib
from collections import Counter, defaultdict
from PIL import Image
import numpy as np
import pandas as pd

BASE_DIR = "/home/jaskirat/PlantDoc-Dataset"

TOMATO_CLASSES = {
    "Tomato leaf bacterial spot": "Bacterial_spot",
    "Tomato Early blight leaf": "Early_blight",
    "Tomato leaf late blight": "Late_blight"
}

def dhash(image, hash_size=8):
    # Difference hash: resize to (hash_size + 1, hash_size), convert to L, compare adjacent pixels
    resized = image.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    pixels = np.asarray(resized)
    diff = pixels[:, 1:] > pixels[:, :-1]
    return diff.flatten()

def hamming_dist(h1, h2):
    return int(np.count_nonzero(h1 != h2))

def analyze_plantdoc():
    print("==================================================")
    print("PLANTDOC DATASET ANALYSIS")
    print("==================================================")
    
    # 1. Overall inventory
    for split in ["train", "test"]:
        split_p = os.path.join(BASE_DIR, split)
        all_imgs = glob.glob(os.path.join(split_p, "*", "*"))
        classes = [d for d in os.listdir(split_p) if os.path.isdir(os.path.join(split_p, d))]
        print(f"Overall PlantDoc {split}: {len(classes)} classes, {len(all_imgs)} image files")
        
    # 2. AgriMind Tomato 3-class subset
    records = []
    bad_files = []
    
    for split in ["train", "test"]:
        split_p = os.path.join(BASE_DIR, split)
        for folder_name, agy_class in TOMATO_CLASSES.items():
            class_p = os.path.join(split_p, folder_name)
            if not os.path.isdir(class_p):
                print(f"Missing folder: {class_p}")
                continue
            files = sorted([f for f in os.listdir(class_p) if os.path.isfile(os.path.join(class_p, f))])
            for f in files:
                filepath = os.path.join(class_p, f)
                size_bytes = os.path.getsize(filepath)
                records.append({
                    "split": split,
                    "folder": folder_name,
                    "class": agy_class,
                    "filename": f,
                    "filepath": filepath,
                    "size_bytes": size_bytes
                })
                
    df = pd.DataFrame(records)
    print(f"\nTotal tomato 3-class images found: {len(df)}")
    
    # Counts per class and split
    pivot_counts = df.pivot_table(index="class", columns="split", values="filename", aggfunc="count", fill_value=0)
    pivot_counts["Total"] = pivot_counts.sum(axis=1)
    print("\n--- Tomato 3-Class Counts by Split ---")
    print(pivot_counts.to_string())
    print("\nSplit totals:")
    print(pivot_counts.sum().to_string())
    
    # Image decoding, formats, dimensions, channels, MD5, dHash, brightness, contrast, dark_frac
    formats = Counter()
    dimensions = Counter()
    channels = Counter()
    md5_dict = defaultdict(list)
    dhashes = []
    stats_list = []
    
    for idx, row in df.iterrows():
        p = row["filepath"]
        
        # MD5
        with open(p, "rb") as f:
            h = hashlib.md5(f.read()).hexdigest()
        md5_dict[h].append((row["split"], row["class"], row["filename"]))
        
        # Pillow verify + decode
        try:
            with Image.open(p) as img:
                img.verify()
            with Image.open(p) as img:
                formats[img.format] += 1
                dimensions[img.size] += 1
                channels[img.mode] += 1
                dh = dhash(img)
                rgb = np.asarray(img.convert("RGB"), dtype=np.float32)
                gray = np.asarray(img.convert("L"), dtype=np.float32)
                
            b = float(gray.mean())
            c = float(gray.std())
            dark = float((gray < 15).mean())
            dhashes.append((row["split"], row["class"], row["filename"], dh))
            stats_list.append({
                "split": row["split"],
                "class": row["class"],
                "brightness": b,
                "contrast": c,
                "dark_frac": dark,
                "width": img.size[0],
                "height": img.size[1]
            })
        except Exception as e:
            bad_files.append((p, str(e)))
            
    print(f"\nIntegrity check failures: {len(bad_files)}")
    print(f"Formats: {dict(formats)}")
    print(f"Color Modes: {dict(channels)}")
    widths = [s["width"] for s in stats_list]
    heights = [s["height"] for s in stats_list]
    print(f"Dimensions - Width: min={min(widths)}, max={max(widths)}, mean={np.mean(widths):.1f}")
    print(f"Dimensions - Height: min={min(heights)}, max={max(heights)}, mean={np.mean(heights):.1f}")
    print(f"Number of distinct dimension pairs: {len(dimensions)}")
    
    # Exact MD5 Duplicates
    dup_md5 = {h: flist for h, flist in md5_dict.items() if len(flist) > 1}
    print(f"\n--- Exact Duplicates (MD5) ---")
    print(f"Unique MD5: {len(md5_dict)} | Duplicate groups: {len(dup_md5)}")
    if dup_md5:
        for h, flist in dup_md5.items():
            print(f"  Hash {h[:8]}...: {flist}")
    else:
        print("  None found!")
        
    # Near-duplicates using dHash
    print(f"\n--- Near-Duplicate Check (dHash Hamming Distance <= 4) ---")
    near_dups = []
    n = len(dhashes)
    for i in range(n):
        for j in range(i + 1, n):
            s1, c1, f1, h1 = dhashes[i]
            s2, c2, f2, h2 = dhashes[j]
            dist = hamming_dist(h1, h2)
            if dist <= 4:
                near_dups.append((dist, s1, c1, f1, s2, c2, f2))
                
    near_dups.sort(key=lambda x: x[0])
    print(f"Total pairs with dHash <= 4: {len(near_dups)}")
    for dist, s1, c1, f1, s2, c2, f2 in near_dups:
        print(f"  Dist {dist}: [{s1} | {c1}] {f1} <---> [{s2} | {c2}] {f2}")
        
    # Verify reported pairs
    print("\nChecking specifically reported pairs from prompt:")
    target_pair_1 = ("bacterial-canker3x2400-2ia1kgd.jpg", "07.17.18-Common_Tomato_Diseases_Canker-258x300.jpg")
    target_pair_2 = ("late_blight1.jpg", "18c.jpg")
    for dist, s1, c1, f1, s2, c2, f2 in near_dups:
        if (f1 in target_pair_1 and f2 in target_pair_1) or (f1 in target_pair_2 and f2 in target_pair_2):
            print(f"  VERIFIED: {f1} and {f2} have dHash distance {dist}")

    # Brightness, Contrast, dark_frac statistics
    df_stats = pd.DataFrame(stats_list)
    print("\n--- Brightness, Contrast & dark_frac by Class ---")
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
    
    print("\n--- Comparison: PlantVillage vs PlantDoc (Measured Quantities) ---")
    print(f"PlantVillage: All 256x256, 100% fixed size, laboratory cutouts/scans")
    print(f"PlantDoc: Variable resolutions ({min(widths)}x{min(heights)} to {max(widths)}x{max(heights)}), unconstrained aspect ratios")
    print(f"PlantDoc dark_frac > 0.3: {(df_stats['dark_frac'] > 0.3).sum()} / {len(df_stats)}")

if __name__ == "__main__":
    analyze_plantdoc()
