# Grand Contract v1.0 — M4 Videos Router
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.video import VideoOut, VideoStatusUpdate
from app.services import auth_service, video_service, queue_service
from app.models.workspace import UserRole

router = APIRouter(prefix="/projects/{project_id}/videos", tags=["videos"])


@router.get("/", response_model=list[VideoOut])
async def list_videos(project_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


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
    # TODO: implement per contract
    pass


@router.get("/{video_id}", response_model=VideoOut)
async def get_video(project_id: UUID, video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


@router.get("/{video_id}/frames/{frame_number}")
async def get_frame(project_id: UUID, video_id: UUID, frame_number: int, current_user=Depends(auth_service.get_current_user)):
    """
    Return extracted JPEG frame as FileResponse.
    Path: FRAME_DIR/{video_id}/{frame_number:05d}.jpg
    Error modes: 404 if frame not yet extracted or out of range.
    """
    # TODO: implement per contract
    pass


@router.get("/{video_id}/trajectories")
async def get_trajectories(project_id: UUID, video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Return trajectory data from parquet as JSON for client-side rendering.
    Response: {"tracks": [{"track_id": int, "frames": [{"f": int, "x": float, "y": float}]}]}
    Aggregated to centroids only (not raw bboxes) to minimize payload.
    """
    # TODO: implement per contract
    pass


@router.post("/{video_id}/queue")
async def queue_video(
    project_id: UUID,
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER)),
    db: AsyncSession = Depends(get_db),
):
    """Manually re-queue a video (e.g. after ERROR). Fires QUEUE_CONTROLLED audit."""
    # TODO: implement per contract
    pass


# Internal endpoint called by worker — not exposed in public OpenAPI docs
@router.patch("/{video_id}/status", include_in_schema=False)
async def update_status(project_id: UUID, video_id: UUID, payload: VideoStatusUpdate, db: AsyncSession = Depends(get_db)):
    """Worker-internal status update. No auth (internal network only)."""
    # TODO: implement per contract
    pass
