"""
Vision Inference Engine for AgriMind (Week 6).
Executes single-image disease classification using the fine-tuned ResNet-50 baseline checkpoint.
Supports in-process execution and cross-environment execution via subprocess without requiring
Pydantic in the vision environment.
"""
import os
import sys
import json
import argparse
from typing import Dict, Any, Optional

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

DEFAULT_CHECKPOINT = os.environ.get(
    "AGRIMIND_MODEL_PATH",
    os.path.join(WORKSPACE_DIR, "outputs", "week2_vision", "best_model.pth")
)
VISION_PYTHON_ENV = "/home/jaskirat/agrimind-vision-env/bin/python"

SUPPORTED_CLASSES = [
    "Tomato___Bacterial_spot",
    "Tomato___Early_blight",
    "Tomato___Late_blight"
]


def verify_image_integrity(image_path: str) -> bool:
    """
    Verifies that an image file exists, is non-empty, and can be decoded by Pillow.
    Executes in-process if Pillow is present, otherwise invokes the dedicated vision environment.
    """
    if not image_path or not os.path.exists(image_path):
        return False

    try:
        from PIL import Image
        with Image.open(image_path) as img:
            img.verify()
        return True
    except (ImportError, ModuleNotFoundError):
        import subprocess
        python_bin = VISION_PYTHON_ENV if os.path.exists(VISION_PYTHON_ENV) else sys.executable
        cmd = [
            python_bin,
            "-c",
            "import sys; from PIL import Image; Image.open(sys.argv[1]).verify()",
            image_path
        ]
        res = subprocess.run(cmd, capture_output=True)
        return res.returncode == 0
    except Exception:
        return False


def run_raw_inference(image_path: str, checkpoint_path: str = DEFAULT_CHECKPOINT, device: str = "cpu") -> Dict[str, Any]:
    """
    Direct ResNet-50 inference function requiring only PyTorch, Torchvision, and Pillow.
    Returns plain Python dictionary (zero Pydantic dependency).
    """
    import torch
    from PIL import Image
    from src.vision.model import create_model
    from src.vision.dataset import get_val_transforms, IDX_TO_LABEL

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")
    if not os.path.exists(checkpoint_path):
        raise FileNotFoundError(f"Vision model checkpoint not found at: {checkpoint_path}")

    model = create_model(num_classes=3, pretrained=False)
    checkpoint = torch.load(checkpoint_path, map_location=device)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    elif isinstance(checkpoint, dict):
        model.load_state_dict(checkpoint)
    else:
        raise ValueError(f"Unrecognized checkpoint format at: {checkpoint_path}")

    model.to(device)
    model.eval()

    img = Image.open(image_path).convert("RGB")
    transform = get_val_transforms(image_size=224)
    tensor = transform(img).unsqueeze(0).to(device)

    with torch.no_grad():
        outputs = model(tensor)
        probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()

    pred_idx = int(probs.argmax())
    pred_class = IDX_TO_LABEL[pred_idx]
    conf = float(probs[pred_idx])
    class_probs = {IDX_TO_LABEL[i]: round(float(probs[i]), 4) for i in range(len(probs))}

    return {
        "predicted_class": pred_class,
        "confidence": conf,
        "class_probabilities": class_probs,
        "model_name": "ResNet-50-Tomato3-Baseline",
        "is_supported_disease": pred_class in SUPPORTED_CLASSES
    }


class VisionInferenceEngine:
    """
    Inference wrapper for the Week 2 ResNet-50 tomato disease classifier.
    Handles image validation, preprocessing, model loading, and softmax probabilities.
    Returns a typed VisionPrediction object.
    """

    def __init__(
        self,
        checkpoint_path: str = DEFAULT_CHECKPOINT,
        device: Optional[str] = None
    ):
        self.checkpoint_path = checkpoint_path
        self.device = device or "cpu"

    def predict(self, image_path: str):
        """
        Classifies an input tomato leaf image.
        Executes in-process if Pillow/torchvision is present, otherwise delegates
        to the dedicated vision environment (/home/jaskirat/agrimind-vision-env).
        Returns a typed VisionPrediction.
        """
        from src.agents.schemas import VisionPrediction

        if not image_path or not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at path: {image_path}")

        try:
            # Attempt in-process inference
            import PIL
            import torchvision
            raw_data = run_raw_inference(image_path, self.checkpoint_path, self.device)
            return VisionPrediction(**raw_data)

        except (ImportError, ModuleNotFoundError):
            # Fall back to invoking the dedicated vision environment
            raw_data = self._predict_via_subprocess(image_path)
            return VisionPrediction(**raw_data)

    def _predict_via_subprocess(self, image_path: str) -> Dict[str, Any]:
        """Invokes dedicated vision environment python when Pillow is absent from caller env."""
        import subprocess

        python_bin = VISION_PYTHON_ENV if os.path.exists(VISION_PYTHON_ENV) else sys.executable
        cmd = [
            python_bin,
            "-m", "src.vision.inference",
            "--image", image_path,
            "--checkpoint", self.checkpoint_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=WORKSPACE_DIR)
        if result.returncode != 0:
            raise RuntimeError(f"Vision inference subprocess failed: {result.stderr.strip()}")

        return json.loads(result.stdout.strip())


def main():
    parser = argparse.ArgumentParser(description="AgriMind Vision Inference")
    parser.add_argument("--image", required=True, help="Path to input tomato leaf image")
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT, help="Model checkpoint path")
    args = parser.parse_args()

    result_dict = run_raw_inference(args.image, checkpoint_path=args.checkpoint)
    print(json.dumps(result_dict))


if __name__ == "__main__":
    main()
