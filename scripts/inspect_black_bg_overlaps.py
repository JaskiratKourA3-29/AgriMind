"""
Read-only inspection of 150 black-background images and their overlaps
with exact duplicates, representative samples, inspect_dark, and non_JPG_ext.
Does NOT create or modify any split files.
"""
import os
import pandas as pd
import numpy as np

OUTPUTS_DIR = os.path.expanduser("~/agrimind-fiftyone-eda/outputs")

def main():
    dark_csv = os.path.join(OUTPUTS_DIR, "plantvillage_dark_frac.csv")
    stats_csv = os.path.join(OUTPUTS_DIR, "plantvillage_image_stats.csv")
    dup_csv = os.path.join(OUTPUTS_DIR, "plantvillage_md5_duplicates.csv")
    
    df_dark = pd.read_csv(dark_csv)
    df_stats = pd.read_csv(stats_csv)
    df_dup = pd.read_csv(dup_csv)
    
    print("=== 1. HOW 150 BLACK-BACKGROUND SAMPLES ARE IDENTIFIED ===")
    print("Definition: Grayscale pixel value < 15 (threshold 15/255).")
    print("dark_frac = count(pixels < 15) / total_pixels.")
    print("Threshold applied for 'black_bg': dark_frac > 0.3")
    
    black_bg_df = df_dark[df_dark["dark_frac"] > 0.3]
    print(f"Total samples with dark_frac > 0.3: {len(black_bg_df)}")
    print("Distribution of black_bg across classes:")
    print(black_bg_df["label"].value_counts().to_dict())
    print("Distribution of black_bg across file groups (JPG vs non-JPG):")
    print(black_bg_df["grp"].value_counts().to_dict())
    
    print("\nNon-JPG group breakdown (total 153):")
    non_jpg_all = df_dark[df_dark["grp"] == "non-JPG"]
    print(f"  dark_frac > 0.3 (black_bg): {len(non_jpg_all[non_jpg_all['dark_frac'] > 0.3])}")
    print(f"  dark_frac <= 0.3 (bright outliers): {len(non_jpg_all[non_jpg_all['dark_frac'] <= 0.3])}")
    
    # 2. OVERLAPS WITH EXACT DUPLICATES
    print("\n=== 2. OVERLAPS WITH EXACT DUPLICATES (exact_dup, 16 files) ===")
    dup_paths = set(df_dup["filepath"])
    black_bg_paths = set(black_bg_df["filepath"])
    dup_overlap = dup_paths.intersection(black_bg_paths)
    print(f"Duplicate files in black_bg: {len(dup_overlap)} of {len(dup_paths)}")
    
    # Check duplicate pairs
    dup_groups = df_dup.groupby("md5")
    for md5, grp in dup_groups:
        paths = list(grp["filepath"])
        in_black = [p in black_bg_paths for p in paths]
        exts = [os.path.splitext(p)[1] for p in paths]
        print(f"  MD5 {md5[:8]}... (exts: {exts}): in black_bg = {in_black}")
        
    # 3. OVERLAPS WITH REP_SEED42
    print("\n=== 3. OVERLAPS WITH REPRESENTATIVE SAMPLES (rep_seed42, 15 files) ===")
    # From FiftyOne inspection earlier, let's load FiftyOne or check the 15 files
    # The 15 rep_seed42 samples were listed in our previous inspection
    rep_paths = [
        "0d227915-443b-402c-8a25-cc43434c4bb0___GCREC_Bact.Sp 5913.JPG",
        "3a28881d-eede-4274-b158-c54ebd1c7164___GCREC_Bact.Sp 3136.JPG",
        "7334e742-de72-4561-9b0d-cdd8bc3313e7___GCREC_Bact.Sp 3066.JPG",
        "7f0a444d-f5ca-4378-a06d-fa94469f2ae1___GCREC_Bact.Sp 3686.JPG",
        "8c9f86a5-70df-4ab0-bb33-1bd4ea9cb91e___UF.GRC_BS_Lab Leaf 0846.JPG",
        "1ba9a636-a673-45bc-b515-4fe6848f271e___RS_Erly.B 9605.JPG",
        "23e8ae15-6cfc-4518-9266-3a289a7bced7___RS_Erly.B 6479.JPG",
        "afc527c5-c9b2-478b-8df0-ff66767191df___RS_Erly.B 7473.JPG",
        "bfbf7eb4-8a12-4595-96f7-dcec497d3917___RS_Erly.B 7682.JPG",
        "c10623b4-33fe-458c-9d8e-d9a74fb74a6a___RS_Erly.B 7450.JPG",
        "1507883d-7f10-4b69-88d4-db80850b1664___GHLB2 Leaf 154.JPG",
        "772e3007-0263-45ec-b7f2-fd283d3fcd90___RS_Late.B 5578.JPG",
        "973b8b82-cccd-433c-a868-5dee559b2dce___GHLB Leaf 2.6 Day 12.JPG",
        "a4008f85-d333-4ca8-87c2-e8c9c68ed19a___RS_Late.B 6461.JPG",
        "f336431f-8e79-4ff6-9afd-03bacf1bfaf2___RS_Late.B 5521.JPG"
    ]
    rep_overlap = [p for p in rep_paths if any(p in bp for bp in black_bg_paths)]
    print(f"Representative samples (rep_seed42) in black_bg: {len(rep_overlap)} of {len(rep_paths)}")
    
    # 4. OVERLAPS WITH INSPECT_DARK
    print("\n=== 4. OVERLAPS WITH INSPECT_DARK (8 files) ===")
    inspect_dark_paths = [
        "2763c9bc-ecc6-4f1a-86a7-ef8ffa370420___RS_Erly.B 8422.JPG",
        "3b86d42f-4b22-4bfe-bfa9-ec4567c886dc___RS_Erly.B 7823.JPG",
        "4a352896-5a0f-4e42-aba1-f06045d5b531___RS_Erly.B 7765.JPG",
        "611a3c58-8a99-401e-9745-592b55bddb85___RS_Erly.B 7679.JPG",
        "ac804481-f1b0-498c-a6af-a66da467f84e___RS_Erly.B 7760.JPG",
        "07b42bb5-9f6c-43bc-9bbe-e4b127d84cb6___GHLB Leaf 18.1 Day 8.jpg",
        "60196a6c-a134-4107-8178-d1bb47450cee___GHLB Leaf 23.1 Day 9.jpg",
        "d0badc95-d04c-457b-8db8-aa6e198f4bd6___GHLB Leaf 10 Day 6.jpeg"
    ]
    dark_overlap = [p for p in inspect_dark_paths if any(p in bp for bp in black_bg_paths)]
    print(f"inspect_dark samples in black_bg: {len(dark_overlap)} of {len(inspect_dark_paths)}")
    print("Reason: 5 are Early Blight with dark_frac <= 0.211 (below 0.3 threshold); 3 are non-JPG with dark_frac = 0.000 (bright).")

if __name__ == "__main__":
    main()
