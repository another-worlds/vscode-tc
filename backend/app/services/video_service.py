# Grand Contract v1.0 — M4 Video Ingestion Service
from __future__ import annotations
import asyncio
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.video import Video, VideoStatus
from app.schemas.video import VideoStatusUpdate
from app.config import settings


async def register_video_from_path(
    filepath: str,
    project_id: UUID,
    uploaded_by: UUID | None,
    db: AsyncSession,
) -> Video:
    """
    Create a Video record from a filesystem path (watcher ingest path).

    Args:
        filepath:    absolute path inside container (VIDEO_DIR/...)
        project_id:  parent project
        uploaded_by: user UUID or None (system watcher)
        db:          async DB session

    Returns:
        Newly created Video ORM object with status=PENDING.

    Side-effects:
        - Probes video metadata (resolution, fps, duration, size) via ffprobe
        - INSERT into videos table

    Error modes:
        - Duplicate filepath: returns existing record if already registered
        - ffprobe failure: fields left as None, video still registered
    """
    stmt = select(Video).where(Video.filepath == filepath)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing

    metadata = await probe_video_metadata(filepath)
    filename = Path(filepath).name

    video = Video(
        project_id=project_id,
        filename=filename,
        filepath=filepath,
        resolution_w=metadata.get("resolution_w"),
        resolution_h=metadata.get("resolution_h"),
        duration_s=metadata.get("duration_s"),
        size_bytes=metadata.get("size_bytes"),
        fps=metadata.get("fps"),
        status=VideoStatus.PENDING,
        uploaded_by=uploaded_by,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    return video


async def probe_video_metadata(filepath: str) -> dict:
    """
    Use ffprobe to extract video metadata.

    Returns:
        {
            "resolution_w": int, "resolution_h": int,
            "duration_s": float, "fps": float, "size_bytes": int
        }

    Performance note: runs ffprobe as subprocess; acceptable for ingest path.
    Error modes: returns empty dict on failure (non-fatal).
    """
    path = Path(filepath)
    if not path.exists():
        return {}

    ffprobe_cmd = shutil.which("ffprobe") or "ffprobe"
    try:
        proc = await asyncio.create_subprocess_exec(
            ffprobe_cmd,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,duration",
            "-show_entries",
            "format=size",
            "-of",
            "json",
            filepath,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return {}
        payload = json.loads(stdout)
        stream = payload.get("streams", [{}])[0]
        fmt = payload.get("format", {})

        width = int(stream.get("width") or 0) or None
        height = int(stream.get("height") or 0) or None
        duration = None
        if stream.get("duration"):
            duration = float(stream.get("duration"))
        elif fmt.get("duration"):
            duration = float(fmt.get("duration"))

        fps = None
        fps_rate = stream.get("r_frame_rate")
        if fps_rate and "/" in fps_rate:
            num, den = fps_rate.split("/")
            if den and int(den) != 0:
                fps = float(num) / float(den)

        size_bytes = None
        if fmt.get("size"):
            size_bytes = int(float(fmt.get("size")))
        else:
            size_bytes = int(path.stat().st_size)

        return {
            "resolution_w": width,
            "resolution_h": height,
            "duration_s": duration,
            "fps": fps,
            "size_bytes": size_bytes,
        }
    except Exception:
        return {}


async def upload_video_ui(
    file_bytes: bytes,
    filename: str,
    project_id: UUID,
    uploaded_by: UUID,
    db: AsyncSession,
) -> Video:
    """
    Handle multipart UI upload: save to VIDEO_DIR, then call register_video_from_path.

    Args:
        file_bytes:   raw MP4 bytes from multipart upload
        filename:     original filename (sanitized before use)
        project_id:   parent project
        uploaded_by:  authenticated user
        db:           async DB session

    Returns:
        Created Video record.

    Security note (OWASP A01): filename is sanitized (Path.name) to prevent path traversal.
    Invariant: only .mp4 extension accepted.
    Error modes:
        - HTTPException 400 if extension is not .mp4
        - HTTPException 413 handled by nginx (client_max_body_size)
    """
    safe_name = Path(filename).name
    if Path(safe_name).suffix.lower() != ".mp4":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only .mp4 uploads are supported.")

    video_dir = Path(settings.VIDEO_DIR)
    video_dir.mkdir(parents=True, exist_ok=True)

    target_path = video_dir / safe_name
    if target_path.exists():
        target_path = video_dir / f"{target_path.stem}_{uuid.uuid4().hex[:8]}{target_path.suffix}"

    target_path.write_bytes(file_bytes)
    return await register_video_from_path(str(target_path), project_id, uploaded_by, db)


async def update_video_status(
    video_id: UUID, update: VideoStatusUpdate, db: AsyncSession
) -> Video:
    """
    Update video status, timestamps, parquet_path, frame_count.
    Called by worker via internal API endpoint.

    Side-effects: DB UPDATE.
    Error modes: HTTPException 404 if video not found.
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    video.status = update.status
    if update.error_message is not None:
        video.error_message = update.error_message
    if update.frame_count is not None:
        video.frame_count = update.frame_count
    if update.parquet_path is not None:
        video.parquet_path = update.parquet_path

    if update.status == VideoStatus.PROCESSING and video.processing_started_at is None:
        video.processing_started_at = datetime.now(timezone.utc)
    if update.status == VideoStatus.PROCESSED:
        video.processed_at = datetime.now(timezone.utc)
    if update.status in {VideoStatus.PENDING, VideoStatus.QUEUED}:
        video.error_message = None

    await db.commit()
    await db.refresh(video)
    return video


async def get_video_frames_dir(video_id: UUID) -> Path:
    """
    Return the directory containing extracted JPEG frames for this video.
    Path: FRAME_DIR/{video_id}/

    Invariant: directory exists iff video.status == PROCESSED.
    """
    return Path(settings.FRAME_DIR) / str(video_id)
