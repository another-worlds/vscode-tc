# Grand Contract v1.0 — M4 Video Ingestion Service
from __future__ import annotations
import uuid
from pathlib import Path
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.video import Video, VideoStatus
from app.schemas.video import VideoOut, VideoStatusUpdate
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
    # TODO: implement per contract
    pass


async def probe_video_metadata(filepath: str) -> dict:
    """
    Use ffmpeg-python to extract video metadata.

    Returns:
        {
            "resolution_w": int, "resolution_h": int,
            "duration_s": float, "fps": float, "size_bytes": int
        }

    Performance note: runs ffprobe as subprocess; acceptable for ingest path.
    Error modes: returns empty dict on failure (non-fatal).
    """
    # TODO: implement per contract
    pass


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
    # TODO: implement per contract
    pass


async def update_video_status(
    video_id: UUID, update: VideoStatusUpdate, db: AsyncSession
) -> Video:
    """
    Update video status, timestamps, parquet_path, frame_count.
    Called by worker via internal API endpoint.

    Side-effects: DB UPDATE.
    Error modes: HTTPException 404 if video not found.
    """
    # TODO: implement per contract
    pass


async def get_video_frames_dir(video_id: UUID) -> Path:
    """
    Return the directory containing extracted JPEG frames for this video.
    Path: FRAME_DIR/{video_id}/

    Invariant: directory exists iff video.status == PROCESSED.
    """
    # TODO: implement per contract
    pass
