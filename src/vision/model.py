"""
ResNet-50 model architecture and fine-tuning utilities.
"""
import torch
import torch.nn as nn
from torchvision import models

def create_model(num_classes=3, pretrained=True):
    """
    Constructs ResNet-50 with pretrained ImageNet-1k weights (V2)
    and a custom linear classification head for 3 classes.
    """
    weights = models.ResNet50_Weights.IMAGENET1K_V2 if pretrained else None
    model = models.resnet50(weights=weights)
    
    in_features = model.fc.in_features
    model.fc = nn.Linear(in_features, num_classes)
    
    # Initialize the new linear layer
    nn.init.kaiming_normal_(model.fc.weight, mode='fan_out', nonlinearity='relu')
    nn.init.constant_(model.fc.bias, 0.0)
    
    return model

def freeze_backbone(model):
    """
    Phase 1 Warmup: Freezes all feature extraction layers,
    leaving only the final linear classifier trainable.
    """
    for name, param in model.named_parameters():
        if "fc" not in name:
            param.requires_grad = False
        else:
            param.requires_grad = True

def unfreeze_backbone(model):
    """
    Phase 2 Fine-tuning: Unfreezes all layers for end-to-end training.
    """
    for param in model.parameters():
        param.requires_grad = True

def count_parameters(model):
    """
    Returns (total_params, trainable_params).
    """
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total, trainable
