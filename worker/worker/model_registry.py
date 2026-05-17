# ════════════════════════════════════════════════════════════════════════════════
# IMMUTABLE MODULE v1.0 — Do not modify unless new explicit contract supersedes.
# Pluggable via deterministic interface.
#
# Module: M6 GPU Worker - YOLO model registry
# Description: Load and cache YOLO models from ultralytics using mounted model cache
# ════════════════════════════════════════════════════════════════════════════════

# Grand Contract v1.0 — M6 GPU Worker: YOLO model registry
# Configurable via YOLO_MODEL_KEY env variable
from __future__ import annotations
from pathlib import Path
import logging
import sys
from ultralytics import YOLO

# Registry: key → model filename (downloaded to model_cache volume)
# Invariant: all keys must be valid ultralytics model names
YOLO_REGISTRY: dict[str, str] = {
    "yolov8n": "yolov8n.pt",
    "yolov8s": "yolov8s.pt",
    "yolov8m": "yolov8m.pt",   # default — best accuracy/speed tradeoff for L4
    "yolov8l": "yolov8l.pt",
    "yolov8x": "yolov8x.pt",
    # Extend here: "yolov9c": "yolov9c.pt", etc.
}

# COCO class IDs relevant to traffic counting
VEHICLE_CLASS_IDS: set[int] = {
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
}

VEHICLE_CLASS_NAMES: dict[int, str] = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
}

logger = logging.getLogger(__name__)
_model_cache: dict[str, YOLO] = {}


def _get_cache_dir() -> Path:
    """Return the ultralytics cache directory inside the mounted model_cache volume."""
    cache_path = Path.home() / ".cache" / "ultralytics"
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def load_model(model_key: str) -> YOLO:
    """
    Load and cache a YOLO model by registry key.

    Args:
        model_key: key from YOLO_REGISTRY (e.g. 'yolov8m')

    Returns:
        Loaded YOLO model instance (cached in memory for worker lifetime).

    Side-effects:
        - Downloads model weights on first call (stored in model_cache volume)
        - GPU memory allocated on first inference call

    Error modes:
        - KeyError if model_key not in YOLO_REGISTRY
        - RuntimeWarning if CUDA unavailable (falls back to CPU)
        - RuntimeError if model fails to load
    """
    if model_key not in YOLO_REGISTRY:
        raise KeyError(f"Unknown YOLO model key: {model_key}")

    if model_key in _model_cache:
        return _model_cache[model_key]

    cache_dir = _get_cache_dir()
    weights_name = YOLO_REGISTRY[model_key]
    weights_path = cache_dir / weights_name

    if weights_path.exists():
        model_source = str(weights_path)
    else:
        # Let ultralytics manage download into its cache volume
        model_source = model_key
        logger.info("Model %s not present locally; allowing ultralytics to download it into %s", model_key, cache_dir)

    try:
        model = YOLO(model_source)
    except Exception as exc:
        logger.error("Failed to load YOLO model '%s': %s", model_key, exc)
        raise RuntimeError(f"Failed to load YOLO model '{model_key}'") from exc

    try:
        import torch

        if torch.cuda.is_available():
            model.to("cuda:0")
            logger.info("YOLO model %s loaded onto CUDA", model_key)
        else:
            logger.warning("CUDA unavailable; YOLO model %s will run on CPU", model_key)
    except Exception as exc:
        logger.warning(
            "Unable to verify CUDA availability for YOLO model %s, using default device: %s",
            model_key,
            exc,
        )

    _model_cache[model_key] = model
    return model


def get_model(model_key: str) -> YOLO:
    """
    Return cached model or load it. Thread-safe for single-worker use.
    Invariant: same model_key always returns the same instance.
    """
    if model_key in _model_cache:
        return _model_cache[model_key]
    return load_model(model_key)
