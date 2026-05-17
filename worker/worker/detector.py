# Grand Contract v1.0 — M6 GPU Worker: YOLOv8 Detector
from __future__ import annotations
import logging
from collections.abc import Generator

import cv2
import numpy as np
from dataclasses import dataclass
from ultralytics import YOLO
from worker.model_registry import VEHICLE_CLASS_IDS

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """Single detection from one frame."""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_id: int
    frame_number: int


def detect_frame(
    model: YOLO,
    frame: np.ndarray,
    frame_number: int,
    conf_threshold: float = 0.25,
    iou_threshold: float = 0.45,
    imgsz: int = 640,
) -> list[Detection]:
    """
    Run YOLOv8 inference on a single BGR frame.

    Args:
        model:          loaded YOLO model
        frame:          BGR numpy array (H, W, 3)
        frame_number:   index of this frame in the video
        conf_threshold: minimum confidence to keep detection
        iou_threshold:  NMS IoU threshold
        imgsz:          inference image size (square)

    Returns:
        List of Detection objects filtered to VEHICLE_CLASS_IDS only.

    Performance notes (2026 best practices):
        - batch_size=1 for streaming; consider batch_size=8 for offline processing
        - half=True (FP16) enabled on L4 GPU for ~2x throughput
        - imgsz=640 optimal for YOLOv8m on 1080p→640p letterboxing

    Error modes:
        - Returns empty list on inference error (logged, non-fatal)
    """
    try:
        import torch

        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    except Exception:
        device = "cpu"

    try:
        results = model(
            frame,
            imgsz=imgsz,
            conf=conf_threshold,
            iou=iou_threshold,
            device=device,
            half=(device != "cpu"),
            verbose=False,
        )
        if not results:
            return []

        result = results[0]
        boxes = getattr(result, "boxes", None)
        if boxes is None:
            return []

        data = getattr(boxes, "data", None)
        if data is None:
            return []

        if hasattr(data, "cpu"):
            data = data.cpu()
        data = np.asarray(data)

        detections: list[Detection] = []
        for row in data:
            x1, y1, x2, y2, confidence, class_id = row[:6]
            class_id = int(class_id)
            if class_id not in VEHICLE_CLASS_IDS:
                continue
            detections.append(
                Detection(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    confidence=float(confidence),
                    class_id=class_id,
                    frame_number=frame_number,
                )
            )
        return detections
    except Exception as exc:
        logger.error("YOLO detection failed on frame %s: %s", frame_number, exc)
        return []


def detect_video_stream(
    model: YOLO,
    video_path: str,
    total_frames: int,
    conf_threshold: float = 0.25,
) -> Generator[tuple[int, list[Detection]], None, None]:
    """
    Generator yielding per-frame Detection lists for all frames in the video.

    Args:
        model:        loaded YOLO model
        video_path:   absolute path to MP4
        total_frames: total frame count (for progress reporting)

    Yields:
        (frame_number, list[Detection]) tuples

    Performance note:
        Uses cv2.VideoCapture with MJPEG acceleration where available.
        Processes every frame (no skip) — tracker requires temporal continuity.

    Error modes:
        - Raises FileNotFoundError if video_path not accessible
        - Logs and skips corrupt frames
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video file not accessible: {video_path}")

    frame_number = 0
    while frame_number < total_frames:
        ret, frame = cap.read()
        if not ret:
            logger.warning("Skipping unreadable frame %s in %s", frame_number, video_path)
            frame_number += 1
            continue

        detections = detect_frame(
            model,
            frame,
            frame_number=frame_number,
            conf_threshold=conf_threshold,
        )
        yield frame_number, detections
        frame_number += 1

    cap.release()
