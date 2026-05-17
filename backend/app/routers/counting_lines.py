# Grand Contract v1.0 — M8 Counting Lines Router
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.counting_line import CountingLineCreate, CountingLineOut, CountingResultOut
from app.services import auth_service, counting_service
from app.models.workspace import UserRole

router = APIRouter(prefix="/videos/{video_id}/lines", tags=["counting-lines"])


@router.get("/", response_model=list[CountingLineOut])
async def list_lines(video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


@router.post("/", response_model=CountingLineOut, status_code=201)
async def create_line(
    video_id: UUID,
    payload: CountingLineCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    """
    Create line, then trigger background counting computation.
    Fires LINE_DRAWN and VIDEO_MARKUP_STARTED audits.
    """
    # TODO: implement per contract
    pass


@router.delete("/{line_id}", status_code=204)
async def delete_line(
    video_id: UUID,
    line_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    # TODO: implement per contract
    pass


@router.get("/{line_id}/result", response_model=CountingResultOut)
async def get_result(video_id: UUID, line_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    # TODO: implement per contract
    pass


@router.get("/heatmap")
async def get_heatmap(video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """Return density grid for trajectory heatmap overlay."""
    # TODO: implement per contract
    pass


@router.get("/suggest")
async def suggest_lines(video_id: UUID, current_user=Depends(auth_service.get_current_user), db: AsyncSession = Depends(get_db)):
    """Return trajectory segment data for client-side cluster suggestion."""
    # TODO: implement per contract
    pass
