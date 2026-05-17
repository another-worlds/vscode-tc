# Grand Contract v1.0 — M4 Videos Router
from pathlib import Path
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.video import VideoOut, VideoStatusUpdate
from app.services import auth_service, video_service, queue_service
from app.models.workspace import UserRole
from app.models.video import Video, VideoStatus
from app.config import settings

router = APIRouter(prefix="/projects/{project_id}/videos", tags=["videos"])


@router.get("/", response_model=list[VideoOut])
async def list_videos(project_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Video).where(Video.project_id == project_id)
    result = await db.execute(stmt)
    videos = result.scalars().all()
    return [VideoOut.from_attributes(video) for video in videos]


@router.post("/upload", response_model=VideoOut, status_code=201)
async def upload_video(
    project_id: UUID,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    """
    Multipart upload: save MP4, register video, enqueue for processing.
    Background task: enqueue_video after response is returned.
    Fires VIDEO_UPLOADED audit.
    """
    file_bytes = await file.read()
    video = await video_service.upload_video_ui(file_bytes, file.filename, project_id, current_user.id, db)
    await video_service.update_video_status(video.id, VideoStatusUpdate(status=VideoStatus.QUEUED), db)
    background_tasks.add_task(queue_service.enqueue_video, video.id, video.filepath, project_id)
    return VideoOut.from_attributes(video)


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(project_id: UUID, video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(Video).where(Video.id == video_id, Video.project_id == project_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return VideoOut.from_attributes(video)


@router.get("/{video_id}/frames/{frame_number}")
async def get_frame(project_id: UUID, video_id: UUID, frame_number: int, current_user=Depends(auth_service.get_current_user)):
    """
    Return extracted JPEG frame as FileResponse.
    Path: FRAME_DIR/{video_id}/{frame_number:05d}.jpg
    Error modes: 404 if frame not yet extracted or out of range.
    """
    frame_path = Path(settings.FRAME_DIR) / str(video_id) / f"{frame_number:05d}.jpg"
    if not frame_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Frame not found")
    return FileResponse(frame_path)


@router.get("/{video_id}/trajectories")
async def get_trajectories(project_id: UUID, video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Return trajectory data from parquet as JSON for client-side rendering.
    Response: {"tracks": [{"track_id": int, "frames": [{"f": int, "x": float, "y": float}]}]}
    Aggregated to centroids only (not raw bboxes) to minimize payload.
    """
    stmt = select(Video).where(Video.id == video_id, Video.project_id == project_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None or video.parquet_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trajectory data not available")
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Trajectory extraction requires parquet support in backend")


@router.post("/{video_id}/queue")
async def queue_video(
    project_id: UUID,
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Manually re-queue a video (e.g. after ERROR). Fires QUEUE_CONTROLLED audit."""
    stmt = select(Video).where(Video.id == video_id, Video.project_id == project_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    await queue_service.enqueue_video(video.id, video.filepath, project_id)
    await video_service.update_video_status(video.id, VideoStatusUpdate(status=VideoStatus.QUEUED), db)
    return {"detail": "Video re-queued"}


# Internal endpoint called by worker — not exposed in public OpenAPI docs
@router.patch("/{video_id}/status", include_in_schema=False)
async def update_status(project_id: UUID, video_id: UUID, payload: VideoStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Worker-internal status update. No auth (internal network only)."""
    video = await video_service.update_video_status(video_id, payload, db)
    return VideoOut.from_attributes(video)
