# Grand Contract v1.0 — M6 GPU Worker: JPEG Frame Extractor
from __future__ import annotations
import logging
from pathlib import Path
import cv2
import numpy as np

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    output_dir: Path,
    sample_count: int = 100,
    jpeg_quality: int = 85,
) -> list[Path]:
    """
    Extract uniformly sampled JPEG keyframes from an MP4.

    Args:
        video_path:   absolute path to MP4 inside container
        output_dir:   FRAME_DIR/{video_id}/ — created if not exists
        sample_count: number of frames to extract (default: FRAMES_SAMPLE_COUNT)
        jpeg_quality: JPEG compression quality 1-100

    Returns:
        List of Paths to written JPEG files, ordered by frame number.
        Filenames: {frame_number:05d}.jpg

    Algorithm:
        total = cap.get(CAP_PROP_FRAME_COUNT)
        indices = np.linspace(0, total-1, sample_count, dtype=int)
        For each index: seek cap to frame, write JPEG.

    Performance note:
        cv2.VideoCapture with CAP_PROP_POS_FRAMES seek is O(1) for MP4 (moov atom at start).
        For files with moov at end (non-faststart), first run `ffmpeg -i in.mp4 -movflags faststart out.mp4`.

    Side-effects:
        - Creates output_dir if not exists
        - Writes sample_count JPEG files

    Error modes:
        - Raises FileNotFoundError if video_path not accessible
        - Returns partial list if some frames are corrupt (logs warning)
        - Returns empty list if video has 0 frames
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f"Video file not accessible: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames <= 0:
        cap.release()
        return []

    indices = get_frame_indices(total_frames, sample_count)
    extracted_paths: list[Path] = []

    for frame_index in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ret, frame = cap.read()
        if not ret or frame is None:
            logger.warning("Unable to read frame %s from %s", frame_index, video_path)
            continue

        success, buffer = cv2.imencode(
            ".jpg",
            frame,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if not success:
            logger.warning("JPEG encode failed for frame %s from %s", frame_index, video_path)
            continue

        output_path = output_dir / f"{frame_index:05d}.jpg"
        output_path.write_bytes(buffer.tobytes())
        extracted_paths.append(output_path)

    cap.release()
    return extracted_paths


def get_frame_indices(total_frames: int, sample_count: int) -> list[int]:
    """
    Compute uniformly spaced frame indices.

    Args:
        total_frames: total frame count from VideoCapture
        sample_count: desired number of samples

    Returns:
        Sorted list of unique integer frame indices.

    Invariant: len(result) == min(sample_count, total_frames)
    """
    if total_frames <= 0:
        return []

    count = min(sample_count, total_frames)
    if count == total_frames:
        return list(range(total_frames))

    indices = np.linspace(0, total_frames - 1, count, dtype=int)
    unique_indices = np.unique(indices).astype(int).tolist()
    if len(unique_indices) < count:
        # Ensure the last frame is included when sample_count is near total_frames
        unique_indices = list(range(count - len(unique_indices))) + unique_indices
        unique_indices = sorted(set(unique_indices))[:count]
    return unique_indices
