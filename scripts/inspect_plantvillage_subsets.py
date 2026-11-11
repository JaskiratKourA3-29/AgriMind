"""
Detailed inspection of inspect_dark, rep_seed42, exact_dup, and sample tags count.
"""
import os
import fiftyone as fo
from PIL import Image

def inspect_samples():
    ds = fo.load_dataset("plantvillage_tomato3")
    
    # 1. Check tags on non-JPG subset
    non_jpg_view = ds.match_tags("non_JPG_ext")
    print("=== NON-JPG SUBSET TAGS ===")
    print("Total samples in non_JPG_ext view:", len(non_jpg_view))
    tag_counts = non_jpg_view.count_sample_tags()
    print("Sample tags on non_JPG_ext view:", tag_counts)
    print("Sum of tag occurrences on non_JPG_ext view:", sum(tag_counts.values()))
    
    # 2. Inspect the 8 inspect_dark samples
    print("\n=== 8 INSPECT_DARK SAMPLES ===")
    dark_view = ds.match_tags("inspect_dark")
    for s in dark_view:
        with Image.open(s.filepath) as im:
            print(f"ID: {s.id} | Label: {s.ground_truth.label} | Ext: {os.path.splitext(s.filepath)[1]} | dark_frac: {s.dark_frac:.3f} | B: {s.brightness:.1f} | C: {s.contrast:.1f} | File: {os.path.basename(s.filepath)}")
            
    # 3. Inspect rep_seed42 samples
    print("\n=== 15 REP_SEED42 SAMPLES ===")
    rep_view = ds.match_tags("rep_seed42")
    for s in rep_view:
        print(f"Label: {s.ground_truth.label} | B: {s.brightness:.1f} | C: {s.contrast:.1f} | dark_frac: {s.dark_frac:.3f} | File: {os.path.basename(s.filepath)}")
        
    # 4. Inspect exact_dup samples
    print("\n=== 16 EXACT_DUP SAMPLES ===")
    dup_view = ds.match_tags("exact_dup")
    groups = {}
    for s in dup_view:
        groups.setdefault(s.md5, []).append((s.filepath, s.brightness, s.contrast))
    for h, flist in groups.items():
        print(f"MD5 {h[:8]}... (size {len(flist)}):")
        for f, b, c in flist:
            print(f"   {os.path.basename(f)} (B={b}, C={c})")

if __name__ == "__main__":
    inspect_samples()
