# Grand Contract v1.0 — M4 Video schemas
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.video import VideoStatus


class VideoOut(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    resolution_w: int | None
    resolution_h: int | None
    duration_s: float | None
    size_bytes: int | None
    fps: float | None
    status: VideoStatus
    error_message: str | None
    uploaded_at: datetime
    uploaded_by: UUID | None
    processing_started_at: datetime | None
    processed_at: datetime | None
    frame_count: int | None
    model_config = {"from_attributes": True}


class VideoStatusUpdate(BaseModel):
    """Internal schema used by worker to update video status."""
    status: VideoStatus
    error_message: str | None = None
    frame_count: int | None = None
    parquet_path: str | None = None
