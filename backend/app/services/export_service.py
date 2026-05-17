# Grand Contract v1.0 — M10 Export Service
from __future__ import annotations
from uuid import UUID
from io import BytesIO
import openpyxl
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.video import Video, VideoStatus
from app.models.counting_line import CountingLine, CountingResult


async def export_counting_results_xlsx(video_id: UUID, db: AsyncSession) -> BytesIO:
    """
    Generate an Excel workbook with counting results for all lines in a video.
    Returns BytesIO seeked to 0.
    """
    stmt = select(Video).where(Video.id == video_id)
    result = await db.execute(stmt)
    video = result.scalar_one_or_none()
    if video is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    if video.status != VideoStatus.PROCESSED:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Video not yet processed")

    # Load all counting lines and results for this video
    lines_stmt = select(CountingLine).where(CountingLine.video_id == video_id)
    lines_result = await db.execute(lines_stmt)
    lines = lines_result.scalars().all()

    if not lines:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No counting lines found")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Summary"

    # Video metadata row
    ws.append(["Video", video.filename or str(video_id)])
    resolution = f"{video.resolution_w}x{video.resolution_h}" if video.resolution_w and video.resolution_h else "unknown"
    ws.append(["Resolution", resolution])
    duration = video.duration_seconds
    ws.append(["Duration (s)", duration or "unknown"])
    ws.append([])

    # Header row
    ws.append(["Line Name", "Count In", "Count Out", "Total", "Vehicle % Breakdown"])

    for line in lines:
        res_stmt = select(CountingResult).where(CountingResult.counting_line_id == line.id)
        res_result = await db.execute(res_stmt)
        counting_result = res_result.scalar_one_or_none()

        if counting_result:
            total = (counting_result.count_in or 0) + (counting_result.count_out or 0)
            pct_str = str(counting_result.vehicle_pct or "")
            ws.append([line.name, counting_result.count_in, counting_result.count_out, total, pct_str])
        else:
            ws.append([line.name, 0, 0, 0, "N/A"])

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer
