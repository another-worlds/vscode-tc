# Grand Contract v1.0 — M8 Counting Lines Router
from uuid import UUID
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.counting_line import CountingLineCreate, CountingLineOut, CountingResultOut
from app.services import auth_service, counting_service
from app.models.workspace import UserRole
from app.models.counting_line import CountingLine, CountingResult

router = APIRouter(prefix="/videos/{video_id}/lines", tags=["counting-lines"])


@router.get("/", response_model=list[CountingLineOut])
async def list_lines(
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CountingLine).where(CountingLine.video_id == video_id)
    result = await db.execute(stmt)
    return result.scalars().all()


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
    """
    line = await counting_service.create_counting_line(video_id, payload, current_user.id, db)
    background_tasks.add_task(counting_service.compute_line_counts, line.id, db)
    return line


@router.delete("/{line_id}", status_code=204)
async def delete_line(
    video_id: UUID,
    line_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    _=Depends(auth_service.require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CountingLine).where(CountingLine.id == line_id, CountingLine.video_id == video_id)
    result = await db.execute(stmt)
    line = result.scalar_one_or_none()
    if line is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line not found")
    await db.delete(line)
    await db.commit()


@router.get("/{line_id}/result", response_model=CountingResultOut)
async def get_result(
    video_id: UUID,
    line_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CountingResult).where(CountingResult.counting_line_id == line_id)
    result = await db.execute(stmt)
    counting_result = result.scalar_one_or_none()
    if counting_result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not computed yet")
    return counting_result


@router.get("/heatmap")
async def get_heatmap(
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return density grid for trajectory heatmap overlay."""
    return await counting_service.get_trajectory_heatmap_data(video_id, db)


@router.get("/suggest")
async def suggest_lines(
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return trajectory segment data for client-side cluster suggestion."""
    return await counting_service.suggest_counting_lines(video_id, db)
