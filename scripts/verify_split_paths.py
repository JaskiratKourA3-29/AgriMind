"""
Verify that 100% of image paths listed in train_split.csv and val_split.csv exist on disk.
"""
import os
import pandas as pd

TRAIN_CSV = "/mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project/data_splits/train_split.csv"
VAL_CSV = "/mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project/data_splits/val_split.csv"

def main():
    df_tr = pd.read_csv(TRAIN_CSV)
    df_va = pd.read_csv(VAL_CSV)
    
    tr_missing = [p for p in df_tr["filepath"] if not os.path.exists(p)]
    va_missing = [p for p in df_va["filepath"] if not os.path.exists(p)]
    
    print(f"Train split rows: {len(df_tr)} | Missing on disk: {len(tr_missing)}")
    print(f"Val split rows: {len(df_va)} | Missing on disk: {len(va_missing)}")
    
    if tr_missing:
        print("Sample missing train files:", tr_missing[:3])
    if va_missing:
        print("Sample missing val files:", va_missing[:3])

if __name__ == "__main__":
    main()
