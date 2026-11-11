"""
Verify PyTorch, Torchvision, CUDA, and dependencies in agrimind-vision-env.
"""
import torch
import torchvision
import pandas as pd
import sklearn
import matplotlib

print(f"PyTorch Version: {torch.__version__}")
print(f"Torchvision Version: {torchvision.__version__}")
print(f"Pandas Version: {pd.__version__}")
print(f"Scikit-Learn Version: {sklearn.__version__}")
print(f"Matplotlib Version: {matplotlib.__version__}")
print(f"CUDA Available: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"CUDA Device Count: {torch.cuda.device_count()}")
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
    print(f"Device Capability: {torch.cuda.get_device_capability(0)}")
    print(f"Allocated VRAM: {torch.cuda.memory_allocated(0)/(1024**2):.1f} MB")
    print(f"Reserved VRAM: {torch.cuda.memory_reserved(0)/(1024**2):.1f} MB")
    
    # Test tensor allocation on CUDA
    x = torch.randn(10, 10, device='cuda')
    y = x @ x.T
    print("CUDA Matrix Multiplication Test: SUCCESS")
else:
    print("WARNING: CUDA is not available!")
