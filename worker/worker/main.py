# Grand Contract v1.0 — M6 GPU Worker: Main processing loop
"""
Worker main loop.

Workflow per job:
    1. BRPOP job from Redis queue
    2. Update video status → PROCESSING (via backend API)
    3. Extract JPEG frames (frame_extractor)
    4. Stream video frames → detect (detector) → track (tracker)
    5. Write trajectories → Parquet (trajectory_writer)
    6. Update video status → PROCESSED with parquet_path + frame_count
    7. On any unhandled exception → status = ERROR with message

Invariant: one job processed at a time (single GPU, no concurrency within worker)
Scale-out: docker compose scale worker=N assigns distinct jobs from shared queue
"""
from __future__ import annotations
import asyncio
import cv2
import json
import logging
from pathlib import Path
from uuid import UUID

import httpx
import redis.asyncio as aioredis

from worker.config import settings
from worker.model_registry import get_model
from worker.detector import detect_video_stream
from worker.tracker import DeepSORTTracker
from worker.trajectory_writer import TrajectoryWriter
from worker.frame_extractor import extract_frames

logger = logging.getLogger(__name__)
JOB_QUEUE_KEY = "job_queue"


async def process_job(job: dict) -> None:
    """
    Execute the full processing pipeline for one video job.

    Args:
        job: {
            "video_id": str,
            "filepath": str,
            "project_id": str,
            "enqueued_at": str
        }

    Side-effects:
        - Writes JPEG frames to FRAME_DIR/{video_id}/
        - Writes trajectories to PARQUET_DIR/{video_id}.parquet
        - PATCHes backend /projects/{project_id}/videos/{video_id}/status

    Error modes:
        - On any exception: PATCH status=ERROR with error_message
        - Logs full traceback
    """
    video_id = job["video_id"]
    project_id = job["project_id"]
    filepath = job["filepath"]

    await update_video_status(video_id, project_id, "PROCESSING")

    frame_dir = Path(settings.FRAME_DIR) / video_id
    frame_paths = extract_frames(
        filepath,
        frame_dir,
        sample_count=settings.FRAMES_SAMPLE_COUNT,
        jpeg_quality=85,
    )

    capture = cv2.VideoCapture(filepath)
    if not capture.isOpened():
        raise FileNotFoundError(f"Video path not accessible: {filepath}")
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    capture.release()

    try:
        writer = TrajectoryWriter(UUID(video_id), settings.PARQUET_DIR)
        tracker = DeepSORTTracker(max_age=settings.TRACKER_MAX_AGE)

        model = get_model(settings.YOLO_MODEL_KEY)
        for frame_number, detections in detect_video_stream(
            model,
            filepath,
            total_frames=total_frames,
            conf_threshold=settings.DETECTOR_CONF,
        ):
            tracked_objects = tracker.update(detections, frame_number)
            writer.append(tracked_objects)

        parquet_path = writer.flush()
        await update_video_status(
            video_id,
            project_id,
            "PROCESSED",
            frame_count=total_frames,
            parquet_path=str(parquet_path),
        )
    except Exception as exc:
        logger.exception("Job %s failed", video_id)
        await update_video_status(video_id, project_id, "ERROR", error_message=str(exc))
        raise


async def update_video_status(
    video_id: str,
    project_id: str,
    status: str,
    error_message: str | None = None,
    frame_count: int | None = None,
    parquet_path: str | None = None,
) -> None:
    """
    Call backend internal API to update video processing status.

    Uses httpx with retry (3x, exponential backoff) for resilience.
    """
    url = f"{settings.BACKEND_URL}/projects/{project_id}/videos/{video_id}/status"
    payload: dict[str, str | int] = {"status": status}
    if error_message is not None:
        payload["error_message"] = error_message
    if frame_count is not None:
        payload["frame_count"] = frame_count
    if parquet_path is not None:
        payload["parquet_path"] = parquet_path

    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(1, 4):
            try:
                response = await client.patch(url, json=payload)
                if response.is_success:
                    return
                logger.warning(
                    "Backend status update failed (%s) on attempt %s: %s %s",
                    status,
                    attempt,
                    response.status_code,
                    response.text,
                )
            except httpx.RequestError as exc:
                logger.warning("Backend request error on attempt %s: %s", attempt, exc)
            await asyncio.sleep(attempt * 1.0)

    logger.error("Unable to update video status after retries: %s -> %s", video_id, status)


async def main() -> None:
    """
    Main worker loop: load model once, then poll Redis for jobs indefinitely.

    Performance note (2026 best practices):
        - Model loaded once at startup → warm inference from job 1
        - Tracker reset between jobs (no state leak between videos)
        - GPU memory NOT freed between jobs (faster iteration)
    """
    logging.basicConfig(level=logging.INFO)
    logger.info("Worker starting. Loading model: %s", settings.YOLO_MODEL_KEY)

    model = get_model(settings.YOLO_MODEL_KEY)
    redis = await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        health_check_interval=30,
    )

    while True:
        try:
            result = await redis.brpop(JOB_QUEUE_KEY, timeout=5)
            if result is None:
                continue

            _key, payload = result
            job = json.loads(payload)
            await process_job(job)
        except Exception as exc:
            logger.error("Worker loop caught exception: %s", exc, exc_info=True)
            await asyncio.sleep(2.0)


if __name__ == "__main__":
    asyncio.run(main())
