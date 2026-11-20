"""
Vision Inference Engine for AgriMind (Week 6 & Cloud Upgrade).
Executes single-image disease classification using the fine-tuned ResNet-50 baseline checkpoint.
Provides in-memory model caching to prevent deserializing 282.6 MB weights on every invocation,
drastically reducing serverless execution latency and memory churn.
"""
import os
import sys
import json
import logging
import argparse
from typing import Dict, Any, Optional
import hashlib
import tempfile
import ipaddress
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)

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
    "Tomato___Late_blight",
    "Tomato___Leaf_Mold",
    "Tomato___Septoria_leaf_spot",
    "Tomato___Spider_mites Two-spotted_spider_mite",
    "Tomato___Target_Spot",
    "Tomato___Tomato_mosaic_virus",
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus"
]
TOMATO_ALL_CLASSES = SUPPORTED_CLASSES + ["Tomato___healthy"]

# Module-level model singleton to eliminate cold-start checkpoint reloads on warm requests
_CACHED_MODEL = None
_CACHED_MODEL_PATH = None
_CACHED_DEVICE = None


ALLOWED_RELEASE_HOSTS = frozenset({
    "github.com",
    "api.github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "github-production-release-asset-2e65be.s3.amazonaws.com",
    "github-production-release-asset-2e65be.s3.us-east-1.amazonaws.com",
})


def is_private_or_reserved_host(hostname: str) -> bool:
    """
    Checks if a hostname or IP string represents localhost, private, loopback,
    link-local, multicast, or reserved address spaces.
    """
    lower_host = hostname.lower().strip()
    if lower_host in ("localhost", "localhost.localdomain", "127.0.0.1", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(lower_host)
        return (
            ip.is_private or
            ip.is_loopback or
            ip.is_link_local or
            ip.is_multicast or
            ip.is_reserved or
            ip.is_unspecified
        )
    except ValueError:
        return False


def validate_release_destination(url: str, allowed_hosts: frozenset = ALLOWED_RELEASE_HOSTS) -> urllib.parse.SplitResult:
    """
    Validates that a URL:
    1. Uses strictly HTTPS.
    2. Contains no embedded user credentials (e.g. user:pass@).
    3. Has a valid non-empty hostname.
    4. Does not point to localhost, private, loopback, or reserved IP spaces.
    5. Host matches the strictly authorized release hosts allowlist.
    """
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"Insecure scheme '{parsed.scheme}'. Only HTTPS is permitted.")
    if parsed.username or parsed.password:
        raise ValueError("URLs containing embedded userinfo/credentials are strictly prohibited.")

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise ValueError("URL contains no valid host.")

    if is_private_or_reserved_host(hostname):
        raise ValueError(f"Prohibited private, loopback, or reserved destination host: {hostname}")

    if hostname not in allowed_hosts:
        raise ValueError(f"Unauthorized destination host '{hostname}'. Expected authorized GitHub release hosts.")

    return parsed


class SecureGitHubReleaseRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Custom redirect handler that validates redirect destinations against strict security rules
    before following any HTTP redirect.
    """
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_release_destination(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


EXPECTED_MODEL_SHA256 = "eb40b4d9ff9bc8278b63392809702fc17dbe701b05974c8a620588ab56c196d5"
EXPECTED_MODEL_SIZE = 282626785


def ensure_model_checkpoint(checkpoint_path: str = DEFAULT_CHECKPOINT) -> str:
    """
    Ensures that the ResNet-50 model checkpoint exists and is verified before loading.
    1. If checkpoint_path exists locally, returns it directly.
    2. In cloud/serverless environments where weights are not bundled, checks ephemeral
       storage (/tmp/agrimind_best_model.pth).
    3. If absent from ephemeral storage, downloads atomically from AGRIMIND_MODEL_URL,
       enforcing strict HTTPS, redirect allowlists, size bounds, and SHA-256 verification.
    """
    if os.path.exists(checkpoint_path):
        return checkpoint_path

    tmp_dir = "/tmp" if os.path.exists("/tmp") else tempfile.gettempdir()
    cloud_cached_path = os.path.join(tmp_dir, "agrimind_best_model.pth")

    if os.path.exists(cloud_cached_path):
        try:
            if os.path.getsize(cloud_cached_path) == EXPECTED_MODEL_SIZE:
                return cloud_cached_path
        except OSError:
            pass

    model_url = os.environ.get("AGRIMIND_MODEL_URL", "").strip()
    if not model_url:
        raise FileNotFoundError(
            f"Vision model checkpoint not found at: {checkpoint_path}. "
            f"Please configure AGRIMIND_MODEL_PATH or AGRIMIND_MODEL_URL for remote retrieval."
        )

    # Validate initial URL against strict HTTPS and release host allowlist
    validate_release_destination(model_url)

    logger.info(f"[VisionEngine] Downloading model checkpoint from remote URL to {cloud_cached_path}...")
    temp_target = f"{cloud_cached_path}.tmp.{os.getpid()}"
    hasher = hashlib.sha256()

    try:
        req = urllib.request.Request(
            model_url,
            headers={"User-Agent": "AgriMind-Backend/1.0"}
        )
        opener = urllib.request.build_opener(SecureGitHubReleaseRedirectHandler)
        bytes_downloaded = 0

        with opener.open(req, timeout=60) as resp, open(temp_target, "wb") as out_f:
            while chunk := resp.read(1048576):
                bytes_downloaded += len(chunk)
                if bytes_downloaded > EXPECTED_MODEL_SIZE:
                    raise ValueError(
                        f"Download stream exceeded expected maximum size ({EXPECTED_MODEL_SIZE} bytes)."
                    )
                hasher.update(chunk)
                out_f.write(chunk)

        if bytes_downloaded < EXPECTED_MODEL_SIZE:
            raise ValueError(
                f"Download was truncated: received {bytes_downloaded} bytes, "
                f"expected exactly {EXPECTED_MODEL_SIZE} bytes."
            )

        computed_sha = hasher.hexdigest()
        if computed_sha != EXPECTED_MODEL_SHA256:
            raise ValueError(
                f"Model integrity verification failed. Expected SHA-256 {EXPECTED_MODEL_SHA256}, got {computed_sha}."
            )

        os.replace(temp_target, cloud_cached_path)
        logger.info("[VisionEngine] Checkpoint successfully downloaded and verified.")
        return cloud_cached_path

    except Exception as e:
        if os.path.exists(temp_target):
            try:
                os.remove(temp_target)
            except OSError:
                pass
        if isinstance(e, (FileNotFoundError, ValueError)):
            raise
        raise RuntimeError(f"Failed to retrieve model checkpoint from remote URL: {e}") from e

def get_or_load_model(checkpoint_path: str = DEFAULT_CHECKPOINT, device: str = "cpu"):
    """
    Returns singleton cached ResNet-50 PyTorch model in RAM.
    Avoids repeatedly deserializing the 282.6 MB checkpoint on consecutive serverless requests.
    """
    global _CACHED_MODEL, _CACHED_MODEL_PATH, _CACHED_DEVICE

    resolved_path = ensure_model_checkpoint(checkpoint_path)
    if _CACHED_MODEL is not None and _CACHED_MODEL_PATH == resolved_path and _CACHED_DEVICE == device:
        return _CACHED_MODEL


    import torch
    from src.vision.model import create_model

    logger.info(f"[VisionEngine] Loading ResNet-50 weights from {resolved_path} on {device}...")
    model = create_model(num_classes=3, pretrained=False)
    checkpoint = torch.load(resolved_path, map_location=device)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
    elif isinstance(checkpoint, dict):
        model.load_state_dict(checkpoint)
    else:
        raise ValueError(f"Unrecognized checkpoint format at: {resolved_path}")

    model.to(device)
    model.eval()

    _CACHED_MODEL = model
    _CACHED_MODEL_PATH = resolved_path
    _CACHED_DEVICE = device
    logger.info("[VisionEngine] Model successfully loaded and cached in memory.")
    return _CACHED_MODEL


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
    Uses cached model instance in RAM for high performance.
    Integrates 2048-D embedding centroid analysis for robust healthy leaf classification
    and out-of-distribution (OOD) uncertainty estimation.
    Returns plain Python dictionary (zero Pydantic dependency).
    """
    import torch
    import numpy as np
    from PIL import Image
    from src.vision.dataset import get_val_transforms, IDX_TO_LABEL

    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at path: {image_path}")

    model = get_or_load_model(checkpoint_path=checkpoint_path, device=device)

    img = Image.open(image_path).convert("RGB")
    transform = get_val_transforms(image_size=224)
    tensor = transform(img).unsqueeze(0).to(device)

    # Register forward hook on avgpool layer to capture 2048-D penultimate feature vector
    features = {}
    def hook_fn(module, input, output):
        features["feat"] = torch.flatten(output, 1)

    hook = model.avgpool.register_forward_hook(hook_fn)
    try:
        with torch.no_grad():
            outputs = model(tensor)
            probs = torch.softmax(outputs, dim=1)[0].cpu().numpy()
    finally:
        hook.remove()

    pred_idx = int(probs.argmax())
    raw_class = IDX_TO_LABEL[pred_idx]
    raw_conf = float(probs[pred_idx])

    centroids_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "class_centroids.npz")
    head_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tomato_classifier_head.npz")

    if os.path.exists(centroids_file) and "feat" in features:
        feat = features["feat"][0].cpu().numpy()
        feat_norm = feat / (np.linalg.norm(feat) + 1e-7)

        c_data = np.load(centroids_file)
        sim_scores = {c_name: float(np.dot(feat_norm, c_data[c_name])) for c_name in c_data.files}
        max_sim = max(sim_scores.values()) if sim_scores else 0.0

        # Out-of-Distribution (OOD) / Non-Plant / Non-Tomato Detection
        # If maximum cosine similarity across all 10 tomato conditions is below 0.44:
        if max_sim < 0.44:
            pred_class = "Tomato___unsupported_or_ambiguous"
            conf = round(float(max_sim), 4)
            is_supported_disease = False
            class_probs = {k: round(v, 4) for k, v in sim_scores.items()}
            class_probs["Tomato___unsupported_or_ambiguous"] = conf
        else:
            # Calibrated Multi-Class Classifier Head
            if os.path.exists(head_file):
                h_data = np.load(head_file)
                coef = h_data["coef"]
                intercept = h_data["intercept"]
                class_names = list(h_data["classes"])

                # Logits: W * x + b with temperature scaling T=1.25 for calibration
                raw_logits = np.dot(coef, feat_norm) + intercept
                T = 1.25
                scaled_logits = raw_logits / T
                exp_logits = np.exp(scaled_logits - np.max(scaled_logits))
                probs_10 = exp_logits / np.sum(exp_logits)

                top_idx = int(np.argmax(probs_10))
                pred_class = class_names[top_idx]
                raw_prob = float(probs_10[top_idx])
                # Cap maximum reported single confidence at 0.95 to eliminate false 100% certainty
                conf = round(float(min(0.95, raw_prob)), 4)
                is_supported_disease = (pred_class != "Tomato___healthy") and (pred_class in SUPPORTED_CLASSES)
                class_probs = {class_names[i]: round(float(probs_10[i]), 4) for i in range(len(class_names))}
            else:
                sorted_sims = sorted(sim_scores.items(), key=lambda x: x[1], reverse=True)
                pred_class = sorted_sims[0][0]
                conf = round(float(min(0.95, sorted_sims[0][1])), 4)
                is_supported_disease = (pred_class != "Tomato___healthy") and (pred_class in SUPPORTED_CLASSES)
                class_probs = {k: round(v, 4) for k, v in sim_scores.items()}
    else:
        pred_class = raw_class
        conf = round(float(min(0.95, raw_conf)), 4)
        is_supported_disease = pred_class in SUPPORTED_CLASSES
        class_probs = {IDX_TO_LABEL[i]: round(float(probs[i]), 4) for i in range(len(probs))}

    return {
        "predicted_class": pred_class,
        "confidence": conf,
        "class_probabilities": class_probs,
        "model_name": "ResNet-50-MultiClass-Calibrated",
        "is_supported_disease": is_supported_disease
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
