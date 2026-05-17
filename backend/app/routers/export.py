# Grand Contract v1.0 — M10 Export Router
from uuid import UUID
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services import auth_service, export_service

router = APIRouter(prefix="/videos/{video_id}/export", tags=["export"])


@router.get("/xlsx")
async def export_xlsx(
    video_id: UUID,
    current_user=Depends(auth_service.get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    Stream Excel export of counting results.
    Content-Disposition: attachment; filename="{video_filename}_results.xlsx"
    Fires RESULTS_DOWNLOADED audit.
    """
    # TODO: implement per contract
    pass
