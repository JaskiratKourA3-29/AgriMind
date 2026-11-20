"""
Dataset definition and transform pipelines for PlantVillage Tomato 3-Class baseline.
"""
import os
import pandas as pd
from PIL import Image
import torch
from torch.utils.data import Dataset
from torchvision import transforms

LABEL_TO_IDX = {
    "Tomato___Bacterial_spot": 0,
    "Tomato___Early_blight": 1,
    "Tomato___Late_blight": 2,
    "Tomato___Leaf_Mold": 3,
    "Tomato___Septoria_leaf_spot": 4,
    "Tomato___Spider_mites Two-spotted_spider_mite": 5,
    "Tomato___Target_Spot": 6,
    "Tomato___Tomato_mosaic_virus": 7,
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": 8,
    "Tomato___healthy": 9,
}
IDX_TO_LABEL = {v: k for k, v in LABEL_TO_IDX.items()}

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

def get_train_transforms(image_size=224):
    """
    Stochastic training augmentations:
    - RandomResizedCrop (scale 0.8 to 1.0)
    - Random horizontal & vertical flips
    - Subtle photometric variation (ColorJitter)
    - Normalization to ImageNet statistics
    """
    return transforms.Compose([
        transforms.RandomResizedCrop(image_size, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.2),
        transforms.ColorJitter(brightness=0.1, contrast=0.1, saturation=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

def get_val_transforms(image_size=224):
    """
    100% deterministic evaluation transforms (ZERO random augmentation):
    - Fixed geometric scaling (Resize to 256)
    - Fixed geometric center crop (CenterCrop to 224)
    - Normalization to ImageNet statistics
    """
    return transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(image_size),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])

class PlantVillageDataset(Dataset):
    """
    Reads from prepared split CSV files.
    Ensures transparent metadata tracking (filepath, is_black_bg, dark_frac).
    """
    def __init__(self, csv_path, transform=None):
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"Split CSV not found at: {csv_path}")
        self.df = pd.read_csv(csv_path)
        self.transform = transform
        
        # Validate labels
        for lbl in self.df["label"].unique():
            if lbl not in LABEL_TO_IDX:
                raise ValueError(f"Unrecognized class label in CSV: {lbl}")
                
    def __len__(self):
        return len(self.df)
        
    def __getitem__(self, idx):
        row = self.df.iloc[idx]
        img_path = row["filepath"]
        label_str = row["label"]
        label_idx = LABEL_TO_IDX[label_str]
        
        with Image.open(img_path) as img:
            img = img.convert("RGB")
            
        if self.transform is not None:
            img_tensor = self.transform(img)
        else:
            img_tensor = transforms.ToTensor()(img)
            
        metadata = {
            "filepath": img_path,
            "filename": row.get("filename", os.path.basename(img_path)),
            "label_str": label_str,
            "is_black_bg": bool(row.get("is_black_bg", False)),
            "dark_frac": float(row.get("dark_frac", 0.0)),
            "md5": str(row.get("md5", "")),
        }
        return img_tensor, label_idx, metadata
