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
    Content-Disposition: attachment; filename="{video_id}_results.xlsx"
    """
    buffer = await export_service.export_counting_results_xlsx(video_id, db)
    headers = {"Content-Disposition": f"attachment; filename={video_id}_results.xlsx"}
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
