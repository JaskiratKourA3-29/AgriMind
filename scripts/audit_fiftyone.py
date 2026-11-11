"""
Audit and verification script for AgriMind Stage 1
"""
import os
import sys

def main():
    import fiftyone as fo
    print("FiftyOne version:", fo.__version__)
    print("Datasets:", fo.list_datasets())
    if "plantvillage_tomato3" in fo.list_datasets():
        ds = fo.load_dataset("plantvillage_tomato3")
        print("Sample count:", len(ds))
        print("Fields:", list(ds.get_field_schema().keys()))
        print("Sample tags:", ds.count_sample_tags())
        print("Labels:", ds.count_values("ground_truth.label"))

if __name__ == "__main__":
    main()
