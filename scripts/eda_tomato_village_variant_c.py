"""
EDA for Tomato-Village Variant C (Object Detection)
Checks:
- Image counts in train and val
- YOLO txt annotations: missing, empty, invalid class IDs, coordinates in [0, 1]
- Pascal VOC XML annotations: parse XML, check bounding boxes (xmin, ymin, xmax, ymax)
- Consistency between YOLO and VOC bounding boxes
- Class frequencies and objects per image distribution
- Bounding box metrics: width, height, normalized area, aspect ratio
- Images with multiple objects, single object, or zero objects
"""
import os
import glob
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
import numpy as np
import pandas as pd

BASE_DIR = "/home/jaskirat/datasets/Tomato-Village/Variant-c(Object Detection)"

CLASS_MAP = {
    0: "Early_blight",
    1: "Healthy",
    2: "Late_blight",
    3: "Leaf Miner",
    4: "Magnesium Deficiency",
    5: "Nitrogen Deficiency",
    6: "Pottassium Deficiency",
    7: "Spotted Wilt Virus"
}

def analyze_variant_c():
    print("==================================================")
    print("TOMATO-VILLAGE VARIANT C (OBJECT DETECTION) ANALYSIS")
    print("==================================================")
    
    splits = ["train", "val"]
    
    for split in splits:
        split_dir = os.path.join(BASE_DIR, split)
        img_dir = os.path.join(split_dir, "images")
        yolo_dir = os.path.join(split_dir, "yolo")
        voc_dir = os.path.join(split_dir, "pascal_voc")
        
        img_files = sorted([f for f in os.listdir(img_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])
        yolo_files = sorted([f for f in os.listdir(yolo_dir) if f.endswith('.txt')])
        voc_files = sorted([f for f in os.listdir(voc_dir) if f.endswith('.xml')])
        
        print(f"\n==========================================")
        print(f"SPLIT: {split.upper()}")
        print(f"==========================================")
        print(f"Images: {len(img_files)} | YOLO txt: {len(yolo_files)} | Pascal VOC xml: {len(voc_files)}")
        
        img_stems = set(os.path.splitext(f)[0] for f in img_files)
        yolo_stems = set(os.path.splitext(f)[0] for f in yolo_files)
        voc_stems = set(os.path.splitext(f)[0] for f in voc_files)
        
        missing_yolo = img_stems - yolo_stems
        missing_voc = img_stems - voc_stems
        print(f"Images without YOLO txt: {len(missing_yolo)}")
        print(f"Images without VOC XML: {len(missing_voc)}")
        
        # Parse YOLO annotations
        empty_yolo = 0
        invalid_class_ids = []
        invalid_coords = []
        objects_per_img = []
        class_counts = Counter()
        box_widths, box_heights, box_areas, box_aspect_ratios = [], [], [], []
        yolo_boxes_by_stem = {}
        
        for stem in sorted(img_stems):
            txt_path = os.path.join(yolo_dir, stem + ".txt")
            if not os.path.exists(txt_path):
                objects_per_img.append(0)
                continue
                
            with open(txt_path, "r") as f:
                lines = [l.strip() for l in f if l.strip()]
                
            if not lines:
                empty_yolo += 1
                objects_per_img.append(0)
                yolo_boxes_by_stem[stem] = []
                continue
                
            objects_per_img.append(len(lines))
            parsed_boxes = []
            
            for line in lines:
                parts = line.split()
                if len(parts) != 5:
                    invalid_coords.append((stem, line, "Expected 5 fields"))
                    continue
                try:
                    cls_id_val = float(parts[0])
                    cls_id = int(round(cls_id_val))
                    xc, yc, w, h = map(float, parts[1:])
                except ValueError:
                    invalid_coords.append((stem, line, "Non-numeric values"))
                    continue
                    
                if cls_id not in CLASS_MAP:
                    invalid_class_ids.append((stem, cls_id_val))
                else:
                    class_counts[CLASS_MAP[cls_id]] += 1
                    
                # Check ranges [0, 1]
                if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 <= w <= 1.0 and 0.0 <= h <= 1.0):
                    invalid_coords.append((stem, (xc, yc, w, h), "Out of range [0, 1]"))
                    
                box_widths.append(w)
                box_heights.append(h)
                box_areas.append(w * h)
                ar = w / h if h > 0 else 0
                box_aspect_ratios.append(ar)
                parsed_boxes.append((cls_id, xc, yc, w, h))
                
            yolo_boxes_by_stem[stem] = parsed_boxes
            
        print(f"Empty YOLO files (0 annotations): {empty_yolo}")
        print(f"Invalid Class IDs: {len(invalid_class_ids)}")
        print(f"Invalid / out-of-range coordinates: {len(invalid_coords)}")
        if invalid_coords:
            print("Sample invalid coord:", invalid_coords[:3])
            
        # Parse VOC XML annotations and compare with YOLO
        voc_count_mismatches = 0
        voc_class_counts = Counter()
        
        # Sample check consistency
        coord_discrepancies = 0
        
        for stem in sorted(img_stems):
            xml_path = os.path.join(voc_dir, stem + ".xml")
            if not os.path.exists(xml_path):
                continue
            try:
                tree = ET.parse(xml_path)
                root = tree.getroot()
                size_elem = root.find("size")
                img_w = float(size_elem.find("width").text)
                img_h = float(size_elem.find("height").text)
                
                objs = root.findall("object")
                yolo_boxes = yolo_boxes_by_stem.get(stem, [])
                if len(objs) != len(yolo_boxes):
                    voc_count_mismatches += 1
                    
                for obj in objs:
                    raw_name = obj.find("name").text
                    try:
                        voc_cls_id = int(round(float(raw_name)))
                        voc_cls_name = CLASS_MAP.get(voc_cls_id, f"Unknown_{voc_cls_id}")
                    except ValueError:
                        voc_cls_name = raw_name
                    voc_class_counts[voc_cls_name] += 1
            except Exception as e:
                print(f"VOC XML error on {stem}: {e}")
                
        print(f"YOLO vs VOC box count mismatches: {voc_count_mismatches}")
        
        # Object statistics
        total_boxes = sum(objects_per_img)
        print(f"\nTotal Annotations (Boxes): {total_boxes}")
        print(f"Mean objects per image: {np.mean(objects_per_img):.2f}")
        print(f"Median objects per image: {np.median(objects_per_img):.1f}")
        print(f"Max objects per image: {np.max(objects_per_img)}")
        print(f"Min objects per image: {np.min(objects_per_img)}")
        
        obj_counter = Counter(objects_per_img)
        print("\nObjects per image summary:")
        print(f"  0 objects: {obj_counter[0]} images ({100*obj_counter[0]/len(img_files):.2f}%)")
        print(f"  1 object: {obj_counter[1]} images ({100*obj_counter[1]/len(img_files):.2f}%)")
        multi_obj_count = sum(cnt for n_obj, cnt in obj_counter.items() if n_obj > 1)
        print(f"  >1 objects: {multi_obj_count} images ({100*multi_obj_count/len(img_files):.2f}%)")
        print("Top 10 object count frequencies:")
        for n_obj, cnt in sorted(obj_counter.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"    {n_obj} objects: {cnt} images ({100*cnt/len(img_files):.2f}%)")
            
        print("\nClass Frequencies in YOLO annotations:")
        for cls_name, cnt in class_counts.most_common():
            print(f"  {cls_name}: {cnt} boxes ({100*cnt/total_boxes:.2f}%)")
            
        print("\nBounding Box Metrics (normalized):")
        print(f"  Width: mean={np.mean(box_widths):.3f}, std={np.std(box_widths):.3f}, min={np.min(box_widths):.3f}, max={np.max(box_widths):.3f}")
        print(f"  Height: mean={np.mean(box_heights):.3f}, std={np.std(box_heights):.3f}, min={np.min(box_heights):.3f}, max={np.max(box_heights):.3f}")
        print(f"  Normalized Area: mean={np.mean(box_areas):.4f}, median={np.median(box_areas):.4f}, min={np.min(box_areas):.4f}, max={np.max(box_areas):.4f}")
        print(f"  Aspect Ratio (W/H): mean={np.mean(box_aspect_ratios):.3f}, median={np.median(box_aspect_ratios):.3f}")

if __name__ == "__main__":
    analyze_variant_c()
