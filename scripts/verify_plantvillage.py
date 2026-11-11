"""
Reproducible verification of PlantVillage EDA and artifacts.
Refuses to overwrite any existing files.
"""
import os
import sys
import hashlib
import pandas as pd
import numpy as np
from PIL import Image

OUTPUTS_DIR = os.path.expanduser("~/agrimind-fiftyone-eda/outputs")

def verify_plantvillage():
    print("=== VERIFYING PLANTVILLAGE EDA ARTIFACTS ===")
    
    # 1. MD5 duplicates CSV
    dup_csv = os.path.join(OUTPUTS_DIR, "plantvillage_md5_duplicates.csv")
    if os.path.exists(dup_csv):
        df_dup = pd.read_csv(dup_csv)
        print(f"Duplicates CSV rows: {len(df_dup)}")
        print(f"Unique MD5s in duplicates CSV: {df_dup['md5'].nunique()}")
        print(f"Group sizes: {df_dup['group_size'].value_counts().to_dict()}")
        print(f"Classes in duplicates: {df_dup['label'].value_counts().to_dict()}")
    else:
        print(f"WARNING: {dup_csv} not found")

    # 2. Image stats CSV
    stats_csv = os.path.join(OUTPUTS_DIR, "plantvillage_image_stats.csv")
    if os.path.exists(stats_csv):
        df_stats = pd.read_csv(stats_csv)
        print(f"\nStats CSV total rows: {len(df_stats)}")
        print("Class counts:")
        for label, count in df_stats['label'].value_counts().items():
            print(f"  {label}: {count} ({100*count/len(df_stats):.2f}%)")
        
        # Extensions
        exts = df_stats['filepath'].apply(lambda p: os.path.splitext(p)[1])
        print("Extension counts:", exts.value_counts().to_dict())
        
        # Non-JPG files
        non_jpg = df_stats[~df_stats['filepath'].str.endswith('.JPG')]
        print(f"Non-.JPG count: {len(non_jpg)}")
        print(f"Non-.JPG classes: {non_jpg['label'].value_counts().to_dict()}")
        all_contain_ghlb = non_jpg['filepath'].apply(lambda p: 'GHLB' in os.path.basename(p)).all()
        print(f"All non-.JPG contain 'GHLB': {all_contain_ghlb}")
        
        # Brightness / Contrast overall and per class
        print("\nBrightness / Contrast per class:")
        for label, grp in df_stats.groupby('label'):
            print(f"  {label}: Brightness mean={grp['brightness'].mean():.2f}, std={grp['brightness'].std():.2f} | Contrast mean={grp['contrast'].mean():.2f}, std={grp['contrast'].std():.2f}")
            
        # Within Late blight: .JPG vs non-.JPG
        lb = df_stats[df_stats['label'].str.contains('Late_blight')]
        lb_jpg = lb[lb['filepath'].str.endswith('.JPG')]
        lb_non_jpg = lb[~lb['filepath'].str.endswith('.JPG')]
        print(f"\nLate blight .JPG (n={len(lb_jpg)}): Brightness mean={lb_jpg['brightness'].mean():.2f}, Contrast mean={lb_jpg['contrast'].mean():.2f}")
        print(f"Late blight non-.JPG (n={len(lb_non_jpg)}): Brightness mean={lb_non_jpg['brightness'].mean():.2f}, Contrast mean={lb_non_jpg['contrast'].mean():.2f}")
        
        # Stats with and without 153 subgroup
        print("\nLate blight WITHOUT 153 non-JPG subgroup:")
        print(f"  n={len(lb_jpg)}, Brightness mean={lb_jpg['brightness'].mean():.2f}, std={lb_jpg['brightness'].std():.2f}, Contrast mean={lb_jpg['contrast'].mean():.2f}, std={lb_jpg['contrast'].std():.2f}")
        print("Late blight WITH 153 non-JPG subgroup (all 1909):")
        print(f"  n={len(lb)}, Brightness mean={lb['brightness'].mean():.2f}, std={lb['brightness'].std():.2f}, Contrast mean={lb['contrast'].mean():.2f}, std={lb['contrast'].std():.2f}")
        
    # 3. Dark fraction CSV
    dark_csv = os.path.join(OUTPUTS_DIR, "plantvillage_dark_frac.csv")
    if os.path.exists(dark_csv):
        df_dark = pd.read_csv(dark_csv)
        print(f"\nDark fraction CSV rows: {len(df_dark)}")
        non_jpg_dark = df_dark[df_dark['grp'] == 'non-JPG']
        jpg_dark = df_dark[df_dark['grp'] == 'JPG']
        print(f"Non-JPG > 0.3 dark_frac: {(non_jpg_dark['dark_frac'] > 0.3).sum()} / {len(non_jpg_dark)}")
        print(f"Non-JPG > 0.5 dark_frac: {(non_jpg_dark['dark_frac'] > 0.5).sum()} / {len(non_jpg_dark)}")
        print(f"JPG > 0.3 dark_frac: {(jpg_dark['dark_frac'] > 0.3).sum()} / {len(jpg_dark)}")
        print(f"Max JPG dark_frac: {jpg_dark['dark_frac'].max():.3f} (Class: {jpg_dark.loc[jpg_dark['dark_frac'].idxmax(), 'label']})")
        print(f"Non-JPG <= 0.3 dark_frac (bright ones): {len(non_jpg_dark[non_jpg_dark['dark_frac'] <= 0.3])}")
        for idx, row in non_jpg_dark[non_jpg_dark['dark_frac'] <= 0.3].iterrows():
            print(f"   {os.path.basename(row['filepath'])}: dark_frac={row['dark_frac']:.3f}")

if __name__ == "__main__":
    verify_plantvillage()
