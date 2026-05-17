# Grand Contract v1.0 — Backend Internal Video Registration Router
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.video import VideoOut
from app.services import video_service, queue_service

router = APIRouter()


@router.post("/internal/videos/register", include_in_schema=False)
async def register_video_internal(
    payload: dict,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a watcher-discovered video file and enqueue it for processing.

    Expected payload:
        - filepath: absolute path to MP4 inside container
        - project_id: UUID string
        - source: optional source label (e.g. "watcher")

    Returns:
        Registered Video record as JSON.

    Error modes:
        - 400 if payload invalid
        - 404 if project_id invalid (deferred to service layer)
    """
    filepath = payload.get("filepath")
    project_id = payload.get("project_id")
    if not filepath or not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="filepath and project_id are required")

    try:
        project_uuid = UUID(project_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id must be a valid UUID")

    video = await video_service.register_video_from_path(filepath, project_uuid, None, db)
    await queue_service.enqueue_video(video.id, video.filepath, project_uuid)
    return VideoOut.from_attributes(video)
